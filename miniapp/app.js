// Putu Piring Uni - Telegram Mini App Client Logic
(function () {
    const tg = window.Telegram?.WebApp;

    // State
    const state = {
        quantity: 1,
        unitPrice: 2.00,
        fulfillmentType: 'delivery', // 'delivery' | 'pickup'
        deliveryFee: 0.50,
        deliveryZone: 'Kawasan UiTM (Kolej Kediaman, PTAR, Lobi Fakulti)',
        deliveryAddress: '',
        customerName: '',
        customerPhone: '',
        notes: ''
    };

    // DOM Elements
    const qtyVal = document.getElementById('qtyVal');
    const btnMinus = document.getElementById('btnMinus');
    const btnPlus = document.getElementById('btnPlus');
    const itemSubtotal = document.getElementById('itemSubtotal');
    const deliveryRadio = document.getElementById('radioDelivery');
    const pickupRadio = document.getElementById('radioPickup');
    const deliveryFields = document.getElementById('deliveryFields');
    const pickupFields = document.getElementById('pickupFields');
    const pickupVenueText = document.getElementById('pickupVenueText');
    const schedulePill = document.getElementById('schedulePill');
    const inputZone = document.getElementById('inputZone');
    const inputAddress = document.getElementById('inputAddress');
    const inputName = document.getElementById('inputName');
    const inputPhone = document.getElementById('inputPhone');
    const inputNotes = document.getElementById('inputNotes');
    const summaryQty = document.getElementById('summaryQty');
    const summaryFoodSubtotal = document.getElementById('summaryFoodSubtotal');
    const summaryDeliveryRow = document.getElementById('summaryDeliveryRow');
    const summaryDeliveryFee = document.getElementById('summaryDeliveryFee');
    const summaryTotalAmount = document.getElementById('summaryTotalAmount');
    const bottomTotalAmount = document.getElementById('bottomTotalAmount');
    const btnSubmit = document.getElementById('btnSubmit');

    // 1. Initialize Telegram WebApp SDK
    function initTelegram() {
        if (!tg) return;

        tg.ready();
        tg.expand();

        // Dynamic theme synchronization ensuring high-contrast readable inputs
        function syncTheme() {
            const isDark = tg.colorScheme === 'dark' || 
                (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);

            if (isDark) {
                document.body.classList.add('dark-mode');
                document.documentElement.classList.remove('light-forced');
                
                const bg = tg.themeParams?.bg_color || '#0f172a';
                const cardBg = tg.themeParams?.secondary_bg_color || '#1e293b';
                const textColor = tg.themeParams?.text_color || '#f8fafc';
                const hintColor = tg.themeParams?.hint_color || '#94a3b8';

                document.documentElement.style.setProperty('--bg-page', bg);
                document.documentElement.style.setProperty('--bg-card', cardBg);
                document.documentElement.style.setProperty('--bottom-bar-bg', cardBg);
                document.documentElement.style.setProperty('--text-main', textColor);
                document.documentElement.style.setProperty('--text-muted', hintColor);
                document.documentElement.style.setProperty('--border', '#334155');
                document.documentElement.style.setProperty('--input-bg', bg);
                document.documentElement.style.setProperty('--input-text', textColor);
                document.documentElement.style.setProperty('--input-border', '#475569');
                document.documentElement.style.setProperty('--input-placeholder', hintColor);
            } else {
                document.body.classList.remove('dark-mode');
                document.documentElement.classList.add('light-forced');

                const bg = tg.themeParams?.bg_color || '#f8fafc';
                const cardBg = tg.themeParams?.secondary_bg_color || '#ffffff';
                const textColor = tg.themeParams?.text_color || '#0f172a';
                const hintColor = tg.themeParams?.hint_color || '#64748b';

                document.documentElement.style.setProperty('--bg-page', bg);
                document.documentElement.style.setProperty('--bg-card', cardBg);
                document.documentElement.style.setProperty('--bottom-bar-bg', '#ffffff');
                document.documentElement.style.setProperty('--text-main', textColor);
                document.documentElement.style.setProperty('--text-muted', hintColor);
                document.documentElement.style.setProperty('--border', '#e2e8f0');
                document.documentElement.style.setProperty('--input-bg', '#ffffff');
                document.documentElement.style.setProperty('--input-text', '#0f172a');
                document.documentElement.style.setProperty('--input-border', '#cbd5e1');
                document.documentElement.style.setProperty('--input-placeholder', '#94a3b8');
            }
        }

        syncTheme();
        if (typeof tg.onEvent === 'function') {
            tg.onEvent('themeChanged', syncTheme);
        }

        // Prefill user details from Telegram
        const user = tg.initDataUnsafe?.user;
        if (user) {
            const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ');
            if (fullName && inputName) {
                inputName.value = fullName;
                state.customerName = fullName;
            }
        }

        // Configure Native Main Button
        if (tg.MainButton) {
            tg.MainButton.onClick(handleOrderSubmission);
        }
    }

    // 2. Schedule Awareness (Malaysia Time UTC+8)
    function setupSchedule() {
        const now = new Date();
        // Convert to UTC+8
        const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
        const mytTime = new Date(utc + (3600000 * 8));
        const day = mytTime.getDay(); // 0 = Sun, 1 = Mon, ..., 6 = Sat

        let scheduleText = '';
        let pickupInfo = '';

        if (day === 0) {
            // Sunday (Ahad)
            scheduleText = '🟢 Buka Hari Ini (Ahad): Kabin UiTM (Pre-order tutup 9:30 AM)';
            pickupInfo = '🏢 <b>Lokasi:</b> Kawasan Kabin UiTM<br>⏰ <b>Waktu:</b> 4:00 PM – 5:00 PM (Ahad Sahaja)<br>💰 <b>Caj:</b> Percuma (RM 0.00)';
        } else if (day === 1 || day === 2 || day === 4) {
            // Monday, Tuesday, Thursday
            const dayNames = ['Ahad', 'Isnin', 'Selasa', 'Rabu', 'Khamis', 'Jumaat', 'Sabtu'];
            scheduleText = `🟢 Buka Hari Ini (${dayNames[day]}): Warung Cik Malik (Pre-order tutup 5:00 PM)`;
            pickupInfo = '🏢 <b>Lokasi:</b> Bersebelahan Warung Santai Cik Malik, 240B Taman Lembah Bujang Utama 8/2, Bedong, Kedah.<br>' +
                         '📍 <a href="https://maps.app.goo.gl/b9YGPZtXLkSVwF4h8" target="_blank">Lihat Panduan Google Maps</a><br>' +
                         '⏰ <b>Waktu:</b> 6:30 PM – 9:00 PM<br>💰 <b>Caj:</b> Percuma (RM 0.00)';
        } else {
            // Wed, Fri, Sat (Closed)
            scheduleText = '🟡 Tutup Hari Ini (Pra-pesanan dibuka untuk hari operasi seterusnya)';
            pickupInfo = '🏢 <b>Lokasi Ambil Sendiri Hari Operasi:</b><br>' +
                         '• <b>Ahad:</b> Kawasan Kabin UiTM (4:00 PM – 5:00 PM)<br>' +
                         '• <b>Isnin, Selasa, Khamis:</b> Sebelah Warung Cik Malik (6:30 PM – 9:00 PM)';
        }

        if (schedulePill) schedulePill.innerHTML = scheduleText;
        if (pickupVenueText) pickupVenueText.innerHTML = pickupInfo;
    }

    // 3. Update Pricing Calculations
    function updateCalculations() {
        const foodSubtotal = state.quantity * state.unitPrice;
        const fee = state.fulfillmentType === 'delivery' ? 0.50 : 0.00;
        state.deliveryFee = fee;
        const total = foodSubtotal + fee;

        if (qtyVal) qtyVal.textContent = state.quantity;
        if (itemSubtotal) itemSubtotal.textContent = `RM ${foodSubtotal.toFixed(2)}`;
        if (summaryQty) summaryQty.textContent = `${state.quantity} set`;
        if (summaryFoodSubtotal) summaryFoodSubtotal.textContent = `RM ${foodSubtotal.toFixed(2)}`;

        if (summaryDeliveryRow) {
            summaryDeliveryRow.style.display = 'flex';
        }
        if (summaryDeliveryFee) {
            summaryDeliveryFee.textContent = state.fulfillmentType === 'delivery' ? 'RM 0.50' : 'Percuma (RM 0.00)';
        }

        const formattedTotal = `RM ${total.toFixed(2)}`;
        if (summaryTotalAmount) summaryTotalAmount.textContent = formattedTotal;
        if (bottomTotalAmount) bottomTotalAmount.textContent = formattedTotal;

        // Sync Telegram MainButton
        if (tg && tg.MainButton) {
            tg.MainButton.setText(`HANTAR PESANAN • ${formattedTotal}`);
            tg.MainButton.show();
            tg.MainButton.enable();
        }
    }

    // 4. Stepper Event Listeners
    if (btnMinus) {
        btnMinus.addEventListener('click', () => {
            if (state.quantity > 1) {
                state.quantity--;
                if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
                updateCalculations();
            }
        });
    }

    if (btnPlus) {
        btnPlus.addEventListener('click', () => {
            if (state.quantity < 30) {
                state.quantity++;
                if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
                updateCalculations();
            }
        });
    }

    // 5. Fulfillment Toggle
    if (deliveryRadio && pickupRadio) {
        deliveryRadio.addEventListener('click', () => {
            state.fulfillmentType = 'delivery';
            deliveryRadio.classList.add('active');
            pickupRadio.classList.remove('active');
            deliveryFields.style.display = 'block';
            pickupFields.style.display = 'none';
            if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
            updateCalculations();
        });

        pickupRadio.addEventListener('click', () => {
            state.fulfillmentType = 'pickup';
            pickupRadio.classList.add('active');
            deliveryRadio.classList.remove('active');
            deliveryFields.style.display = 'none';
            pickupFields.style.display = 'block';
            if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
            updateCalculations();
        });
    }

    // 6. Handle Order Submission
    function handleOrderSubmission() {
        const name = inputName ? inputName.value.trim() : '';
        const phone = inputPhone ? inputPhone.value.trim() : '';
        const zone = inputZone ? inputZone.value : '';
        const address = inputAddress ? inputAddress.value.trim() : '';
        const notes = inputNotes ? inputNotes.value.trim() : '';

        // Validation
        if (!name) {
            alert('Sila masukkan nama penuh anda untuk pesanan.');
            inputName?.focus();
            if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
            return;
        }

        if (!phone || phone.replace(/\D/g, '').length < 9) {
            alert('Sila masukkan nombor telefon / WhatsApp yang sah (cth: 01139163313).');
            inputPhone?.focus();
            if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
            return;
        }

        if (state.fulfillmentType === 'delivery') {
            if (!address) {
                alert('Sila nyatakan lokasi spesifik serahan (cth: Kolej Dahlia 2, Bilik 310 / Lobi PTAR).');
                inputAddress?.focus();
                if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
                return;
            }
        }

        const foodSubtotal = state.quantity * state.unitPrice;
        const totalAmount = foodSubtotal + state.deliveryFee;

        const payload = {
            source: 'miniapp',
            app: 'putu_piring_uni',
            customer_name: name,
            customer_phone: phone,
            package_id: 'pakej-1',
            package_name: 'Pakej 1: Putu Piring Asli (2 biji)',
            quantity: state.quantity,
            unit_price: state.unitPrice,
            food_subtotal: foodSubtotal,
            fulfillment_type: state.fulfillmentType,
            delivery_zone: state.fulfillmentType === 'delivery' ? zone : '',
            delivery_address: state.fulfillmentType === 'delivery' ? address : 'Ambil Sendiri (Self-Pickup)',
            delivery_fee: state.deliveryFee,
            total_amount: totalAmount,
            notes: notes,
            telegram_user: tg?.initDataUnsafe?.user?.username ? `@${tg.initDataUnsafe.user.username}` : '',
            telegram_id: tg?.initDataUnsafe?.user?.id || null,
            submitted_at: new Date().toISOString()
        };

        if (tg?.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('success');
        }

        // Send data directly back into the Telegram Chat
        if (tg && typeof tg.sendData === 'function') {
            try {
                tg.sendData(JSON.stringify(payload));
                return;
            } catch (err) {
                console.error('Error in tg.sendData:', err);
            }
        }

        // Fallback for standalone browser testing
        const jsonStr = JSON.stringify(payload, null, 2);
        alert(`[Pesanan Dihantar! (Mod Ujian Pelayar)]\n\n${jsonStr}`);
    }

    if (btnSubmit) {
        btnSubmit.addEventListener('click', handleOrderSubmission);
    }

    // Startup
    setupSchedule();
    updateCalculations();
    initTelegram();
})();
