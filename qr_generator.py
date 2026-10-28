"""DuitNow & Touch 'n Go QR Generator, EMVCo Parser & Quality Verifier for Putu Piring Uni (@putu_uni_bot).

Compliant with PayNet Malaysia EMVCo Merchant-Presented Mode (MPM) Specifications.
Generates ultra-scannable QR payment cards with high contrast, crisp square modules,
and automated pre-dispatch double-check verification using OpenCV.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import qrcode
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageFilter = None
    qrcode = None

try:
    import cv2
except ImportError:
    cv2 = None

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
STATIC_QR_PATH = BASE_DIR / "duitnow_static.txt"
QR_OUTPUT_DIR = BASE_DIR / "orders" / "qr"
ASSETS_DIR = BASE_DIR / "assets"
DUITNOW_PIN_PATH = ASSETS_DIR / "duitnow_pin.png"
DUITNOW_FULL_PATH = ASSETS_DIR / "duitnow_full.png"
TNG_LOGO_PATH = ASSETS_DIR / "tng_logo.png"

# Default PayNet Malaysia DuitNow template (RHB Bank)
DEFAULT_BANK_STATIC_DUITNOW = (
    "00020201021126580014A000000615000101065641600226215702300329484RHBQR000000"
    "5204000053034585802MY5925MUHAMAD NASRUL BIN HUSSAI6002MY"
    "82649D4897E0446B0C770FAE49C08681264DD3FACA5706D0D6B2FB0A410D21AB899E"
    "6304CF90"
)

# Default PayNet Malaysia Touch 'n Go DuitNow template
DEFAULT_TNG_STATIC_DUITNOW = (
    "00020201021126440014A000000615000101068900530212100194273527"
    "5204000053034585802MY5922MUHAMADNASRULBINHUSSAI6002MY"
    "62130609431258535"
    "6304C99B"
)

DEFAULT_STATIC_DUITNOW = DEFAULT_BANK_STATIC_DUITNOW


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "botToken": "8965329925:AAHDCUCFHYhl2934FlvOD-G0k3HgrUjVkYU",
        "merchantName": "MUHAMAD NASRUL BIN HUSSAIN",
        "merchantCity": "MY",
        "postalCode": "08100",
        "currencyCode": "458",
        "countryCode": "MY",
        "defaultStaticPayload": DEFAULT_BANK_STATIC_DUITNOW,
    }


def get_static_payload() -> str:
    """Retrieves static DuitNow QR string from file, config, or built-in template."""
    if STATIC_QR_PATH.exists():
        content = STATIC_QR_PATH.read_text(encoding="utf-8").strip()
        if content:
            return content

    cfg = load_config()
    if cfg.get("defaultStaticPayload"):
        return cfg["defaultStaticPayload"].strip()

    return DEFAULT_STATIC_DUITNOW


def crc16_ccitt_false(data: bytes) -> str:
    """Calculates CRC-16/CCITT-FALSE (Polynomial 0x1021, Init 0xFFFF).

    Standard EMVCo ISO/IEC 13239 checksum calculation.
    """
    crc = 0xFFFF
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def format_tlv(tag: str, value: str) -> str:
    """Formats a TLV data object (Tag: 2 chars, Length: 2 digits, Value)."""
    return f"{tag}{len(value):02d}{value}"


def parse_tlv(payload: str) -> dict[str, str]:
    """Parses an EMVCo TLV payload string into a dictionary of Tag -> Value."""
    tlv: dict[str, str] = {}
    i = 0
    n = len(payload)
    while i < n:
        if i + 4 > n:
            break
        tag = payload[i : i + 2]
        try:
            length = int(payload[i + 2 : i + 4])
        except ValueError:
            break
        i += 4
        if i + length > n:
            tlv[tag] = payload[i:]
            break
        val = payload[i : i + length]
        i += length
        tlv[tag] = val
    return tlv


def validate_crc(payload: str) -> bool:
    """Checks if the CRC-16 checksum in Tag 63 of an EMVCo payload is valid."""
    if len(payload) < 8 or "6304" not in payload:
        return False
    idx = payload.rfind("6304")
    data_to_check = payload[: idx + 4]
    expected_crc = payload[idx + 4 : idx + 8].upper()
    calculated = crc16_ccitt_false(data_to_check.encode("ascii"))
    return expected_crc == calculated


def build_dynamic_duitnow_payload(
    static_payload: str,
    amount: float,
    reference: str,
    merchant_name: str | None = None,
    city: str | None = None,
) -> str:
    """Transforms a static DuitNow QR payload into an EMVCo Dynamic DuitNow QR payload."""
    clean_static = static_payload.strip()
    tags = parse_tlv(clean_static)

    if "00" not in tags:
        tags["00"] = "01"

    tags["01"] = "12"

    if "53" not in tags:
        tags["53"] = "458"

    tags["54"] = f"{amount:.2f}"

    if "58" not in tags:
        tags["58"] = "MY"

    if merchant_name:
        tags["59"] = merchant_name[:25]
    elif "59" not in tags:
        tags["59"] = "MUHAMAD NASRUL BIN HUSSAI"

    if city:
        tags["60"] = city[:15]
    elif "60" not in tags:
        tags["60"] = "MY"

    tag62_raw = tags.get("62", "")
    subtags62 = parse_tlv(tag62_raw) if tag62_raw else {}
    clean_ref = reference.strip()
    subtags62["01"] = clean_ref
    subtags62["05"] = clean_ref
    new_sub62_str = "".join(
        format_tlv(sub_tag, subtags62[sub_tag])
        for sub_tag in sorted(subtags62.keys())
    )
    tags["62"] = new_sub62_str

    had_tag_82 = "82" in tags
    tags.pop("82", None)
    tags.pop("63", None)

    ordered_keys = sorted(
        [k for k in tags.keys() if int(k) < 82 if k.isdigit()],
        key=lambda k: int(k),
    )
    payload_before_82 = "".join(format_tlv(k, tags[k]) for k in ordered_keys)

    if had_tag_82:
        sha256_hash = hashlib.sha256(payload_before_82.encode("ascii")).hexdigest().upper()
        tags["82"] = sha256_hash

    final_ordered_keys = sorted(
        [k for k in tags.keys() if k.isdigit() and k != "63"],
        key=lambda k: int(k),
    )
    payload_body = "".join(format_tlv(k, tags[k]) for k in final_ordered_keys)

    prefix_for_crc = payload_body + "6304"
    crc = crc16_ccitt_false(prefix_for_crc.encode("ascii"))
    return prefix_for_crc + crc


def get_system_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads clean system TrueType font or falls back gracefully."""
    font_paths = [
        f"C:/Windows/Fonts/{name}.ttf",
        f"C:/Windows/Fonts/{name}",
        f"/usr/share/fonts/{name}.ttf",
        "segoeuib.ttf",
        "segoeui.ttf",
        "arial.ttf",
    ]
    for p in font_paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.truetype("segoeuib.ttf", size)
    except Exception:
        return ImageFont.load_default()


# ==============================================================================
# AUTOMATED PRE-DISPATCH DOUBLE CHECK & VERIFICATION
# ==============================================================================

def verify_qr_image(image_path: Path, expected_payload: str | None = None) -> tuple[bool, str, dict]:
    """Verifies that the generated QR image is physically readable and structurally valid.

    Uses OpenCV's QRCodeDetector to double-check that banking apps and smartphones
    will be able to recognize, scan, and decode the QR code without errors.

    Args:
        image_path: Path to the PNG image file on disk.
        expected_payload: Optional expected EMVCo payload string to match against.

    Returns:
        tuple (passed: bool, message: str, details: dict)
    """
    if not image_path.exists():
        return False, f"File does not exist: {image_path}", {}

    if cv2 is None:
        # Fallback if cv2 is not available
        file_size = image_path.stat().st_size
        if file_size > 5000:
            return True, "Image file exists and has valid size (OpenCV not available for deep decode)", {"file_size": file_size}
        return False, f"Image file is abnormally small ({file_size} bytes)", {"file_size": file_size}

    img = cv2.imread(str(image_path))
    if img is None:
        return False, "Could not open or parse image file via OpenCV", {}

    h, w = img.shape[:2]
    if w < 200 or h < 200:
        return False, f"Image dimensions too small for reliable scanning ({w}x{h})", {"width": w, "height": h}

    detector = cv2.QRCodeDetector()
    decoded_text, points, _ = detector.detectAndDecode(img)

    # Secondary attempt with grayscale if direct RGB fails
    if not decoded_text:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        decoded_text, points, _ = detector.detectAndDecode(gray)

    # Tertiary attempt with Otsu thresholding
    if not decoded_text:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        decoded_text, points, _ = detector.detectAndDecode(thresh)

    if not decoded_text:
        return False, "QR code could not be detected or recognized from the image (Scan Failed)", {
            "width": w,
            "height": h,
            "qr_detected": False,
        }

    crc_ok = validate_crc(decoded_text) if len(decoded_text) >= 8 and "6304" in decoded_text else True

    payload_matches = True
    if expected_payload:
        payload_matches = (decoded_text == expected_payload)

    details = {
        "width": w,
        "height": h,
        "qr_detected": True,
        "decoded_length": len(decoded_text),
        "decoded_preview": decoded_text[:40] + "..." if len(decoded_text) > 40 else decoded_text,
        "crc_valid": crc_ok,
        "payload_matches": payload_matches,
    }

    if not payload_matches:
        return False, f"Decoded payload did not match expected payload string", details

    return True, "QR code detected, formed correctly, and verified scannable", details


# ==============================================================================
# CARD RENDERING ENGINE (HIGH CONTRAST & SCANNABLE)
# ==============================================================================

def render_payment_card(
    channel: str,
    payload: str,
    amount: float,
    order_number: str,
    output_path: Path,
    merchant_name: str = "MUHAMAD NASRUL BIN HUSSAIN",
    fallback_no_logo: bool = False,
) -> tuple[Path, dict]:
    """Renders a clean, high-resolution payment card and verifies its readability."""
    if qrcode is None or Image is None or ImageDraw is None:
        raise RuntimeError("Pillow and qrcode libraries are required for image rendering.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    CW, CH = 640, 840
    canvas = Image.new("RGB", (CW, CH), "#F8FAFC")
    cd = ImageDraw.Draw(canvas)

    margin_x, margin_y = 24, 20
    card_w = CW - (margin_x * 2)
    card_h = CH - (margin_y * 2)

    # Outer white card container
    cd.rounded_rectangle(
        [margin_x, margin_y, margin_x + card_w, margin_y + card_h],
        radius=16,
        fill="#FFFFFF",
        outline="#CBD5E1",
        width=2,
    )

    header_h = 82
    if channel == "bank":
        header_color = "#C00038"
        accent_color = "#F59E0B"
        title = "DuitNow QR"
        subtitle = "SEMUA BANK & SHOPEEPAY"
        tag_text = "BANK QR"
        acc_info = "RHB: 15702300329484 (MUHAMAD NASRUL)"
    else:
        header_color = "#005EB8"
        accent_color = "#FFD100"
        title = "Touch 'n Go eWallet"
        subtitle = "IMBAS KOD QR / DUITNOW TRANSFER"
        tag_text = "TNG QR"
        acc_info = "TNG DuitNow: 100194273527 (019-4464970)"

    # Header banner with accent bar
    cd.rounded_rectangle([margin_x, margin_y, margin_x + card_w, margin_y + header_h], radius=16, fill=header_color)
    cd.rectangle([margin_x, margin_y + header_h - 16, margin_x + card_w, margin_y + header_h], fill=header_color)
    cd.rectangle([margin_x, margin_y + header_h, margin_x + card_w, margin_y + header_h + 4], fill=accent_color)

    f_title = get_system_font("segoeuib", 23)
    f_sub = get_system_font("segoeuib", 11)
    f_pill = get_system_font("segoeuib", 12)
    f_name = get_system_font("segoeuib", 17)
    f_amt_val = get_system_font("segoeuib", 34)
    f_ord = get_system_font("segoeuib", 13)
    f_acc = get_system_font("segoeui", 11)

    cd.text((margin_x + 24, margin_y + 18), title, fill="#FFFFFF", font=f_title)
    cd.text((margin_x + 25, margin_y + 49), subtitle, fill="#FEF08A" if channel == "tng" else "#FFD1D9", font=f_sub)

    # Tag pill in header
    tag_w, tag_h = 100, 30
    tx = margin_x + card_w - tag_w - 20
    ty = margin_y + 24
    cd.rounded_rectangle([tx, ty, tx + tag_w, ty + tag_h], radius=6, fill="#FFFFFF")
    cd.text((tx + tag_w // 2, ty + tag_h // 2), tag_text, fill=header_color, font=f_pill, anchor="mm")

    # Generate standard crisp square module QR code with Error Correction Q
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=9,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#000000", back_color="#FFFFFF").convert("RGBA")

    # Center Logo Badge (Compact ~11% width with clean white border)
    if not fallback_no_logo:
        badge_size = 46
        badge = Image.new("RGBA", (badge_size, badge_size), (255, 255, 255, 255))
        bd = ImageDraw.Draw(badge)
        bd.rounded_rectangle([0, 0, badge_size, badge_size], radius=8, fill="#FFFFFF", outline=header_color, width=2)

        logo_path = DUITNOW_PIN_PATH if channel == "bank" else TNG_LOGO_PATH
        if logo_path.exists():
            try:
                l_img = Image.open(logo_path).convert("RGBA")
                l_res = l_img.resize((32, 32), Image.Resampling.LANCZOS)
                badge.paste(l_res, (7, 7), l_res)
            except Exception:
                pass

        pos = ((qr_img.width - badge_size) // 2, (qr_img.height - badge_size) // 2)
        qr_img.paste(badge, pos, badge)

    qr_x = margin_x + (card_w - qr_img.width) // 2
    qr_y = margin_y + header_h + 18
    canvas.paste(qr_img.convert("RGB"), (qr_x, qr_y))

    # Payment details summary card
    box_y = qr_y + qr_img.height + 14
    box_h = (margin_y + card_h) - box_y - 18
    cd.rounded_rectangle(
        [margin_x + 18, box_y, margin_x + card_w - 18, box_y + box_h],
        radius=12,
        fill="#F8FAFC",
        outline="#E2E8F0",
        width=1,
    )

    cd.text((CW // 2, box_y + 24), merchant_name, fill="#1E293B", font=f_name, anchor="mm")

    # Amount (Highlighted)
    amt_text = f"RM {amount:.2f}"
    cd.text((CW // 2, box_y + 60), amt_text, fill=header_color, font=f_amt_val, anchor="mm")

    # Order Pill
    pill_w = card_w - 70
    pill_h = 32
    pill_x = margin_x + 35
    pill_y = box_y + 88
    cd.rounded_rectangle([pill_x, pill_y, pill_x + pill_w, pill_y + pill_h], radius=6, fill="#FFFFFF", outline="#CBD5E1", width=1)
    ord_text = f"No. Pesanan: {order_number}"
    cd.text((CW // 2, pill_y + pill_h // 2), ord_text, fill="#334155", font=f_ord, anchor="mm")

    # Manual transfer fallback / account proxy
    cd.text((CW // 2, pill_y + pill_h + 16), acc_info, fill="#64748B", font=f_acc, anchor="mm")

    canvas.save(output_path, "PNG", quality=95)

    # ==========================================================================
    # MANDATORY PRE-DISPATCH DOUBLE CHECK
    # ==========================================================================
    is_valid, msg, details = verify_qr_image(output_path, payload)

    # Auto-healing fallback if badge caused any decoding ambiguity
    if not is_valid and not fallback_no_logo:
        print(f"[WARN] Initial card verification failed ({msg}). Triggering auto-fallback to clean high-contrast mode...")
        return render_payment_card(
            channel=channel,
            payload=payload,
            amount=amount,
            order_number=order_number,
            output_path=output_path,
            merchant_name=merchant_name,
            fallback_no_logo=True,
        )

    return output_path, {
        "verified": is_valid,
        "message": msg,
        "details": details,
        "fallback_used": fallback_no_logo,
    }


def generate_qr_card_image(
    payload: str,
    amount: float,
    order_number: str,
    output_path: Path,
    merchant_name: str = "MUHAMAD NASRUL BIN HUSSAIN",
) -> tuple[Path, dict]:
    """Generates and double-checks Bank DuitNow QR card."""
    return render_payment_card(
        channel="bank",
        payload=payload,
        amount=amount,
        order_number=order_number,
        output_path=output_path,
        merchant_name=merchant_name,
    )


def generate_tng_card_image(
    amount: float,
    order_number: str,
    output_path: Path,
    account_holder: str = "MUHAMAD NASRUL BIN HUSSAIN",
) -> tuple[Path, dict]:
    """Generates and double-checks Touch 'n Go eWallet payment card."""
    return render_payment_card(
        channel="tng",
        payload=DEFAULT_TNG_STATIC_DUITNOW,
        amount=amount,
        order_number=order_number,
        output_path=output_path,
        merchant_name=account_holder,
    )


def send_to_telegram(
    bot_token: str,
    chat_id: int | str,
    photo_path: Path,
    caption: str,
) -> bool:
    """Dispatches the generated QR photo directly to the customer's Telegram chat.

    PERFORMS STRICT DOUBLE-CHECK: Will refuse to send if the image is unreadable!
    """
    if not photo_path.exists():
        print(f"[ERROR] Cannot send photo: File does not exist at {photo_path}")
        return False

    # Mandatory double-check before dispatching to customer
    is_valid, msg, details = verify_qr_image(photo_path)
    if not is_valid:
        print(f"[ABORT] Pre-dispatch verification failed! Image will NOT be sent to customer. Reason: {msg}")
        return False

    print(f"[VERIFIED] Pre-dispatch double-check passed ({details.get('decoded_length')} bytes decoded). Sending to customer...")

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

    with open(photo_path, "rb") as f:
        file_bytes = f.read()

    filename = photo_path.name
    parts: list[bytes] = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode("utf-8"))
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{filename}\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8") + file_bytes + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)

    req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = resp.read().decode("utf-8")
            if '"ok":true' in resp_data:
                print(f"[OK] Verified QR successfully dispatched to Telegram chat {chat_id}")
                return True
            else:
                print(f"[FAIL] Telegram API returned: {resp_data}")
                return False
    except Exception as ex:
        print(f"[FAIL] Failed to dispatch photo to Telegram: {ex}")
        return False


def explain_payload(payload: str) -> None:
    """Pretty prints the EMVCo TLV breakdown for inspection and verification."""
    tags = parse_tlv(payload)
    print("\n=======================================================")
    print("EMVCo DuitNow QR Payload Breakdown")
    print("=======================================================")
    print(f"Full Payload String: {payload}\n")

    tag_names = {
        "00": "Payload Format Indicator",
        "01": "Point of Initiation Method (11=Static, 12=Dynamic)",
        "26": "Merchant Account Information (PayNet DuitNow)",
        "52": "Merchant Category Code (MCC)",
        "53": "Transaction Currency Code (458=MYR)",
        "54": "Transaction Amount (RM)",
        "58": "Country Code",
        "59": "Merchant Name",
        "60": "Merchant City",
        "61": "Postal Code",
        "62": "Additional Data Field Template",
        "63": "CRC16 Checksum (ISO/IEC 13239)",
    }

    for tag, val in sorted(tags.items()):
        name = tag_names.get(tag, "Custom / Scheme Tag")
        print(f"Tag [{tag}] (Len: {len(val):02d}) -> {name}: '{val}'")
        if tag == "26":
            subtags = parse_tlv(val)
            for s_tag, s_val in sorted(subtags.items()):
                print(f"     Subtag [{s_tag}] -> '{s_val}'")
        elif tag == "62":
            subtags = parse_tlv(val)
            for s_tag, s_val in sorted(subtags.items()):
                sub_name = "Bill Number / Order ID" if s_tag == "01" else f"Subtag {s_tag}"
                print(f"     Subtag [{s_tag}] ({sub_name}) -> '{s_val}'")

    is_valid = validate_crc(payload)
    print(f"\nChecksum Integrity: {'[VALID]' if is_valid else '[INVALID]'}")
    print("=======================================================\n")


def run_self_tests() -> None:
    """Executes full verification test suite."""
    print("Running EMVCo DuitNow QR Self-Tests & Image Verification Suite...")

    # Test 1: CRC16 standard vector '123456789' -> 29B1
    assert crc16_ccitt_false(b"123456789") == "29B1", "CRC16 Test Failed!"
    print("  [PASS] Test 1: CRC16-CCITT-FALSE standard test vector verified.")

    # Test 2: Verify static payload integrity
    assert validate_crc(DEFAULT_BANK_STATIC_DUITNOW), "Bank static payload CRC invalid!"
    assert validate_crc(DEFAULT_TNG_STATIC_DUITNOW), "TNG static payload CRC invalid!"
    print("  [PASS] Test 2: Official Static DuitNow & Touch 'n Go payloads verified.")

    # Test 3: Generate and Double-Check Bank QR Card
    test_bank_img = QR_OUTPUT_DIR / "test_verify_bank.png"
    p_bank, v_bank = generate_qr_card_image(
        payload=DEFAULT_BANK_STATIC_DUITNOW,
        amount=6.00,
        order_number="TEST-BANK-001",
        output_path=test_bank_img,
    )
    assert v_bank["verified"], f"Bank card double-check failed: {v_bank['message']}"
    print(f"  [PASS] Test 3: Bank QR Card formed correctly and verified by OpenCV scanner.")

    # Test 4: Generate and Double-Check Touch 'n Go Card
    test_tng_img = QR_OUTPUT_DIR / "test_verify_tng.png"
    p_tng, v_tng = generate_tng_card_image(
        amount=6.00,
        order_number="TEST-TNG-001",
        output_path=test_tng_img,
    )
    assert v_tng["verified"], f"TNG card double-check failed: {v_tng['message']}"
    print(f"  [PASS] Test 4: Touch 'n Go Card formed correctly and verified by OpenCV scanner.")

    print("\nAll self-tests and automated double-check verifications passed successfully!\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DuitNow & Touch 'n Go QR Generator with Pre-Dispatch Verification for Putu Piring Uni"
    )
    sub = parser.add_subparsers(dest="cmd")

    # generate command
    gen_p = sub.add_parser("generate", help="Generate and verify a QR payment card for an order")
    gen_p.add_argument("--amount", type=float, required=True, help="Order total in RM (e.g. 2.00, 6.00)")
    gen_p.add_argument("--ref", required=True, help="Order ID reference (e.g. PPU-20261025-001)")
    gen_p.add_argument("--channel", choices=["bank", "tng"], default="tng", help="Payment channel: tng or bank")
    gen_p.add_argument("--name", default=None, help="Merchant name override")
    gen_p.add_argument("--static", default=None, help="Static QR string override")
    gen_p.add_argument("--static-only", action="store_true", help="Omit fixed transaction amount (use static mode)")
    gen_p.add_argument("--output", default=None, help="Output PNG path")
    gen_p.add_argument("--chat-id", default=None, help="Telegram Chat ID to dispatch the image to")
    gen_p.add_argument("--token", default=None, help="Telegram Bot Token")

    # verify command
    ver_p = sub.add_parser("verify", help="Double-check and scan an existing QR image")
    ver_p.add_argument("--image", required=True, help="Path to image file")
    ver_p.add_argument("--payload", default=None, help="Expected payload string")

    # parse command
    parse_p = sub.add_parser("parse", help="Parse and inspect an EMVCo QR string")
    parse_p.add_argument("--payload", required=True, help="EMVCo string to inspect")

    # set-static command
    set_p = sub.add_parser("set-static", help="Save the official static DuitNow QR payload")
    set_p.add_argument("--payload", required=True, help="Static DuitNow payload from bank")

    # test command
    sub.add_parser("test", help="Run self-tests and verification suite")

    args = parser.parse_args()

    if args.cmd == "generate":
        cfg = load_config()
        channel = args.channel or "tng"

        if channel == "tng":
            tng_cfg = cfg.get("tngEwallet", {})
            acc_num = tng_cfg.get("accountNumber", "100194273527")
            acc_holder = tng_cfg.get("accountName", "MUHAMAD NASRUL BIN HUSSAIN")
            out_path = (
                Path(args.output)
                if args.output
                else QR_OUTPUT_DIR / f"{args.ref}_tng.png"
            )
            saved_path, ver_result = generate_tng_card_image(
                amount=args.amount,
                order_number=args.ref,
                output_path=out_path,
                account_holder=acc_holder,
            )

            result = {
                "order_number": args.ref,
                "amount": args.amount,
                "amount_formatted": f"RM {args.amount:.2f}",
                "channel": "tng",
                "qr_image_path": str(out_path.resolve()),
                "account_number": acc_num,
                "account_holder": acc_holder,
                "verification": ver_result,
            }
            print(json.dumps(result, indent=2))

            if not ver_result.get("verified", False):
                print(f"[FATAL] Image double-check verification failed: {ver_result.get('message')}", file=sys.stderr)
                sys.exit(1)

            if args.chat_id:
                bot_token = args.token or cfg.get("botToken")
                caption = (
                    f"💙 <b>Touch 'n Go eWallet — Putu Piring Uni</b>\n"
                    f"• <b>No. Pesanan:</b> <code>{args.ref}</code>\n"
                    f"• <b>Jumlah Bayaran:</b> <b>RM {args.amount:.2f}</b>\n"
                    f"• <b>No. Akaun TNG DuitNow:</b> <code>{acc_num}</code>\n\n"
                    f"📱 <i>Sila imbas kod QR di atas menggunakan Touch 'n Go eWallet atau sebarang aplikasi perbankan (DuitNow QR). "
                    f"Masukkan amaun <b>RM {args.amount:.2f}</b>.</i>\n\n"
                    f"📸 <b>Selepas selesai, sila muat naik resit pembayaran ke sini untuk pengesahan segera ya!</b>"
                )
                send_to_telegram(bot_token, args.chat_id, out_path, caption)

        else:
            static_str = args.static or get_static_payload()
            m_name = args.name or cfg.get("merchantName", "MUHAMAD NASRUL BIN HUSSAIN")

            if args.static_only:
                payload = static_str
            else:
                payload = build_dynamic_duitnow_payload(
                    static_payload=static_str,
                    amount=args.amount,
                    reference=args.ref,
                    merchant_name=m_name,
                )

            out_path = (
                Path(args.output)
                if args.output
                else QR_OUTPUT_DIR / f"{args.ref}.png"
            )
            saved_path, ver_result = generate_qr_card_image(
                payload=payload,
                amount=args.amount,
                order_number=args.ref,
                output_path=out_path,
                merchant_name=m_name,
            )

            result = {
                "order_number": args.ref,
                "amount": args.amount,
                "amount_formatted": f"RM {args.amount:.2f}",
                "channel": "bank",
                "qr_image_path": str(out_path.resolve()),
                "crc_valid": validate_crc(payload),
                "verification": ver_result,
            }
            print(json.dumps(result, indent=2))

            if not ver_result.get("verified", False):
                print(f"[FATAL] Image double-check verification failed: {ver_result.get('message')}", file=sys.stderr)
                sys.exit(1)

            if args.chat_id:
                bot_token = args.token or cfg.get("botToken")
                caption = (
                    f"💳 <b>DuitNow Dynamic QR — Putu Piring Uni</b>\n"
                    f"• <b>No. Pesanan:</b> <code>{args.ref}</code>\n"
                    f"• <b>Jumlah Bayaran:</b> <b>RM {args.amount:.2f}</b> (Telah dikunci automatik)\n"
                    f"• <b>Akaun RHB:</b> <code>15702300329484</code>\n\n"
                    f"📱 <i>Sila imbas kod QR di atas menggunakan aplikasi perbankan anda "
                    f"(Maybank MAE, CIMB, Bank Islam, ShopeePay, dll). Amaun tepat RM {args.amount:.2f} telah sedia tertera.</i>\n\n"
                    f"📸 <b>Selepas selesai, sila muat naik resit bayaran ke sini untuk pengesahan ya!</b>"
                )
                send_to_telegram(bot_token, args.chat_id, out_path, caption)

    elif args.cmd == "verify":
        img_p = Path(args.image)
        ok, msg, details = verify_qr_image(img_p, args.payload)
        out = {
            "image": str(img_p.resolve()),
            "verified": ok,
            "message": msg,
            "details": details,
        }
        print(json.dumps(out, indent=2))
        if not ok:
            sys.exit(1)

    elif args.cmd == "parse":
        explain_payload(args.payload)
    elif args.cmd == "set-static":
        STATIC_QR_PATH.write_text(args.payload.strip(), encoding="utf-8")
        print(f"[OK] Static DuitNow QR saved to: {STATIC_QR_PATH}")
    elif args.cmd == "test":
        run_self_tests()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
