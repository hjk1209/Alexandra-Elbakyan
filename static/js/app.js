(function () {
    const soundStorageKey = 'redeRaizesSocialista.notificationSoundEnabled';
    const popupStorageKey = 'redeRaizesSocialista.browserPopupEnabled';
    const storyDraftStorageKey = 'redeRaizesSocialista.storyDraft';
    const storyDraftSubmittedKey = 'redeRaizesSocialista.storyDraftSubmitted';
    const flashNodes = Array.from(document.querySelectorAll('[data-notification-level]'));
    const soundToggle = document.querySelector('[data-sound-toggle]');
    const popupToggle = document.querySelector('[data-popup-toggle]');
    const storyEditor = document.querySelector('[data-story-editor]');
    let audioContext = null;
    let interactionArmed = false;
    let hasPlayedPending = false;
    let hasShownPendingPopup = false;

    function readPreference(key, fallbackValue) {
        try {
            const stored = window.localStorage.getItem(key);
            return stored === null ? fallbackValue : stored === 'true';
        } catch (error) {
            return fallbackValue;
        }
    }

    function writePreference(key, value) {
        try {
            window.localStorage.setItem(key, String(value));
        } catch (error) {
            return;
        }
    }

    function readJson(key) {
        try {
            const raw = window.localStorage.getItem(key);
            return raw ? JSON.parse(raw) : null;
        } catch (error) {
            return null;
        }
    }

    function writeJson(key, value) {
        try {
            window.localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            return;
        }
    }

    function removeStorageItem(key) {
        try {
            window.localStorage.removeItem(key);
        } catch (error) {
            return;
        }
    }

    function isSoundEnabled() {
        return readPreference(soundStorageKey, true);
    }

    function isPopupEnabled() {
        return readPreference(popupStorageKey, false);
    }

    function updateSoundToggle() {
        if (!soundToggle) {
            return;
        }
        const enabled = isSoundEnabled();
        soundToggle.textContent = enabled ? 'Som: ligado' : 'Som: desligado';
        soundToggle.setAttribute('aria-pressed', enabled ? 'true' : 'false');
    }

    function browserPopupStatus() {
        if (!('Notification' in window)) {
            return 'unsupported';
        }
        if (window.Notification.permission === 'denied') {
            return 'blocked';
        }
        if (isPopupEnabled() && window.Notification.permission === 'granted') {
            return 'enabled';
        }
        return 'disabled';
    }

    function updatePopupToggle() {
        if (!popupToggle) {
            return;
        }

        const status = browserPopupStatus();
        if (status === 'unsupported') {
            popupToggle.textContent = 'Popup: indisponivel';
            popupToggle.setAttribute('aria-pressed', 'false');
            popupToggle.disabled = true;
            return;
        }

        popupToggle.disabled = false;
        if (status === 'blocked') {
            popupToggle.textContent = 'Popup: bloqueado';
            popupToggle.setAttribute('aria-pressed', 'false');
            return;
        }

        if (status === 'enabled') {
            popupToggle.textContent = 'Popup: ligado';
            popupToggle.setAttribute('aria-pressed', 'true');
            return;
        }

        popupToggle.textContent = 'Popup web';
        popupToggle.setAttribute('aria-pressed', 'false');
    }

    function normalizeLevel(rawLevel) {
        const level = String(rawLevel || '').toLowerCase();
        if (level.includes('error')) {
            return 'error';
        }
        if (level.includes('warning')) {
            return 'warning';
        }
        if (level.includes('success')) {
            return 'success';
        }
        return 'info';
    }

    function getAudioContext() {
        if (audioContext) {
            return audioContext;
        }
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextClass) {
            return null;
        }
        audioContext = new AudioContextClass();
        return audioContext;
    }

    function scheduleTone(context, startAt, frequency, duration, peakGain, type) {
        const oscillator = context.createOscillator();
        const gainNode = context.createGain();
        oscillator.type = type || 'sine';
        oscillator.frequency.setValueAtTime(frequency, startAt);
        gainNode.gain.setValueAtTime(0.0001, startAt);
        gainNode.gain.exponentialRampToValueAtTime(peakGain, startAt + 0.01);
        gainNode.gain.exponentialRampToValueAtTime(0.0001, startAt + duration);
        oscillator.connect(gainNode);
        gainNode.connect(context.destination);
        oscillator.start(startAt);
        oscillator.stop(startAt + duration + 0.03);
    }

    function playPattern(level) {
        if (!isSoundEnabled()) {
            return Promise.resolve(false);
        }
        const context = getAudioContext();
        if (!context) {
            return Promise.resolve(false);
        }

        return context.resume().then(function () {
            const start = context.currentTime + 0.02;
            if (level === 'error') {
                scheduleTone(context, start, 220, 0.18, 0.08, 'square');
                scheduleTone(context, start + 0.22, 180, 0.22, 0.07, 'square');
                return true;
            }
            if (level === 'warning') {
                scheduleTone(context, start, 420, 0.12, 0.05, 'triangle');
                scheduleTone(context, start + 0.16, 360, 0.12, 0.05, 'triangle');
                return true;
            }
            if (level === 'success') {
                scheduleTone(context, start, 520, 0.12, 0.05, 'sine');
                scheduleTone(context, start + 0.16, 660, 0.16, 0.05, 'sine');
                return true;
            }
            scheduleTone(context, start, 440, 0.14, 0.045, 'sine');
            return true;
        }).catch(function () {
            return false;
        });
    }

    function getPendingLevels() {
        return flashNodes.map(function (node) {
            return normalizeLevel(node.dataset.notificationLevel);
        });
    }

    function getPendingMessages() {
        return flashNodes.map(function (node) {
            return {
                level: normalizeLevel(node.dataset.notificationLevel),
                text: node.textContent.trim(),
            };
        }).filter(function (entry) {
            return entry.text;
        });
    }

    function mostUrgentLevel(levels) {
        if (levels.includes('error')) {
            return 'error';
        }
        if (levels.includes('warning')) {
            return 'warning';
        }
        if (levels.includes('success')) {
            return 'success';
        }
        return levels[0] || 'info';
    }

    function playPendingNotifications() {
        const pendingLevels = getPendingLevels();
        if (hasPlayedPending || pendingLevels.length === 0 || !isSoundEnabled()) {
            return;
        }

        playPattern(mostUrgentLevel(pendingLevels)).then(function (played) {
            if (played) {
                hasPlayedPending = true;
                return;
            }
            armFirstInteractionPlayback();
        });
    }

    function armFirstInteractionPlayback() {
        const pendingLevels = getPendingLevels();
        if (interactionArmed || pendingLevels.length === 0 || hasPlayedPending || !isSoundEnabled()) {
            return;
        }
        interactionArmed = true;

        const unlockAndPlay = function () {
            interactionArmed = false;
            window.removeEventListener('pointerdown', unlockAndPlay);
            window.removeEventListener('keydown', unlockAndPlay);
            playPendingNotifications();
        };

        window.addEventListener('pointerdown', unlockAndPlay, { once: true, passive: true });
        window.addEventListener('keydown', unlockAndPlay, { once: true });
    }

    function popupTitleForLevel(level) {
        if (level === 'error') {
            return 'Rede Raizes Socialista - erro';
        }
        if (level === 'warning') {
            return 'Rede Raizes Socialista - alerta';
        }
        if (level === 'success') {
            return 'Rede Raizes Socialista - confirmado';
        }
        return 'Rede Raizes Socialista - aviso';
    }

    function showBrowserPopup(level, text) {
        if (browserPopupStatus() !== 'enabled') {
            return false;
        }

        try {
            const notification = new window.Notification(popupTitleForLevel(level), {
                body: text,
                tag: 'rede-raizes-socialista-flash',
            });
            notification.onclick = function () {
                window.focus();
                notification.close();
            };
            return true;
        } catch (error) {
            return false;
        }
    }

    function showPendingBrowserPopups() {
        const pendingMessages = getPendingMessages();
        if (hasShownPendingPopup || pendingMessages.length === 0 || browserPopupStatus() !== 'enabled') {
            return;
        }

        hasShownPendingPopup = pendingMessages.some(function (entry) {
            return showBrowserPopup(entry.level, entry.text);
        });
    }

    function handleSoundToggleClick() {
        const nextValue = !isSoundEnabled();
        writePreference(soundStorageKey, nextValue);
        updateSoundToggle();
        if (nextValue) {
            playPattern('success').then(function (played) {
                if (!played) {
                    armFirstInteractionPlayback();
                }
            });
            return;
        }
        hasPlayedPending = true;
    }

    function syncPopupPreferenceWithPermission() {
        if (browserPopupStatus() === 'blocked') {
            writePreference(popupStorageKey, false);
        }
    }

    function handlePopupToggleClick() {
        if (!('Notification' in window)) {
            updatePopupToggle();
            return;
        }

        if (window.Notification.permission === 'denied') {
            writePreference(popupStorageKey, false);
            updatePopupToggle();
            return;
        }

        if (browserPopupStatus() === 'enabled') {
            writePreference(popupStorageKey, false);
            hasShownPendingPopup = true;
            updatePopupToggle();
            return;
        }

        window.Notification.requestPermission().then(function (permission) {
            if (permission === 'granted') {
                writePreference(popupStorageKey, true);
                updatePopupToggle();
                const played = showBrowserPopup('success', 'Popups do navegador ativados para a Rede Raizes Socialista.');
                if (!played) {
                    showPendingBrowserPopups();
                }
                return;
            }
            writePreference(popupStorageKey, false);
            updatePopupToggle();
        }).catch(function () {
            writePreference(popupStorageKey, false);
            updatePopupToggle();
        });
    }

    function normalizeStoryCaption(value) {
        return String(value || '').trim() || 'Seu texto do story aparece aqui.';
    }

    function normalizeStoryMusic(label, url) {
        const cleanLabel = String(label || '').trim();
        const cleanUrl = String(url || '').trim();
        if (cleanLabel && cleanUrl) {
            return cleanLabel + ' • link pronto';
        }
        if (cleanLabel) {
            return cleanLabel;
        }
        if (cleanUrl) {
            return 'Link de musica adicionado';
        }
        return 'Sem musica definida';
    }

    function setMultiSelectValue(select, values) {
        if (!select) {
            return;
        }
        const selectedValues = Array.isArray(values) ? values.map(String) : [];
        Array.from(select.options).forEach(function (option) {
            option.selected = selectedValues.includes(option.value);
        });
    }

    function readMultiSelectValue(select) {
        if (!select) {
            return [];
        }
        return Array.from(select.selectedOptions).map(function (option) {
            return option.value;
        });
    }

    function setupStoryEditor() {
        if (!storyEditor) {
            try {
                if (window.sessionStorage.getItem(storyDraftSubmittedKey) === 'true') {
                    removeStorageItem(storyDraftStorageKey);
                    window.sessionStorage.removeItem(storyDraftSubmittedKey);
                }
            } catch (error) {
                return;
            }
            return;
        }

        const captionField = storyEditor.querySelector('[name="caption"]');
        const mediaField = storyEditor.querySelector('[name="media"]');
        const backgroundField = storyEditor.querySelector('[name="background_style"]');
        const visibilityField = storyEditor.querySelector('[name="visibility"]');
        const viewersField = storyEditor.querySelector('[name="allowed_viewers"]');
        const replyScopeField = storyEditor.querySelector('[name="reply_scope"]');
        const respondersField = storyEditor.querySelector('[name="allowed_responders"]');
        const musicLabelField = storyEditor.querySelector('[name="music_label"]');
        const musicUrlField = storyEditor.querySelector('[name="music_url"]');
        const durationField = storyEditor.querySelector('[name="duration_hours"]');
        const clearDraftButton = document.querySelector('[data-story-draft-clear]');
        const previewCard = document.querySelector('[data-story-preview-card]');
        const previewMedia = document.querySelector('[data-story-preview-media]');
        const previewCaption = document.querySelector('[data-story-preview-caption]');
        const previewMusic = document.querySelector('[data-story-preview-music]');
        const previewDuration = document.querySelector('[data-story-preview-duration]');
        const previewClasses = ['story-preview-forest', 'story-preview-sunset', 'story-preview-soil', 'story-preview-sky'];
        let mediaObjectUrl = null;

        function cleanupPreviewObjectUrl() {
            if (mediaObjectUrl) {
                window.URL.revokeObjectURL(mediaObjectUrl);
                mediaObjectUrl = null;
            }
        }

        function persistDraft() {
            writeJson(storyDraftStorageKey, {
                caption: captionField ? captionField.value : '',
                background_style: backgroundField ? backgroundField.value : 'forest',
                visibility: visibilityField ? visibilityField.value : 'community',
                allowed_viewers: readMultiSelectValue(viewersField),
                reply_scope: replyScopeField ? replyScopeField.value : 'visible',
                allowed_responders: readMultiSelectValue(respondersField),
                music_label: musicLabelField ? musicLabelField.value : '',
                music_url: musicUrlField ? musicUrlField.value : '',
                duration_hours: durationField ? durationField.value : '24',
            });
        }

        function updatePreview() {
            if (!previewCard) {
                return;
            }

            const backgroundValue = backgroundField && backgroundField.value ? backgroundField.value : 'forest';
            previewCard.classList.remove.apply(previewCard.classList, previewClasses);
            previewCard.classList.add('story-preview-' + backgroundValue);

            if (previewCaption) {
                previewCaption.textContent = normalizeStoryCaption(captionField && captionField.value);
            }
            if (previewMusic) {
                previewMusic.textContent = normalizeStoryMusic(
                    musicLabelField && musicLabelField.value,
                    musicUrlField && musicUrlField.value
                );
            }
            if (previewDuration) {
                previewDuration.textContent = (durationField && durationField.value ? durationField.value : '24') + 'h';
            }

            if (previewMedia) {
                cleanupPreviewObjectUrl();
                previewMedia.innerHTML = '<span>Sem imagem ainda</span>';
                if (mediaField && mediaField.files && mediaField.files[0]) {
                    mediaObjectUrl = window.URL.createObjectURL(mediaField.files[0]);
                    previewMedia.innerHTML = '<img src="' + mediaObjectUrl + '" alt="Preview do story">';
                }
            }
        }

        function restoreDraft() {
            const draft = readJson(storyDraftStorageKey);
            if (!draft) {
                updatePreview();
                return;
            }
            if (captionField && !captionField.value) {
                captionField.value = draft.caption || '';
            }
            if (backgroundField && draft.background_style) {
                backgroundField.value = draft.background_style;
            }
            if (visibilityField && draft.visibility) {
                visibilityField.value = draft.visibility;
            }
            if (replyScopeField && draft.reply_scope) {
                replyScopeField.value = draft.reply_scope;
            }
            if (musicLabelField && !musicLabelField.value) {
                musicLabelField.value = draft.music_label || '';
            }
            if (musicUrlField && !musicUrlField.value) {
                musicUrlField.value = draft.music_url || '';
            }
            if (durationField && (!durationField.value || durationField.value === '24')) {
                durationField.value = draft.duration_hours || '24';
            }
            setMultiSelectValue(viewersField, draft.allowed_viewers);
            setMultiSelectValue(respondersField, draft.allowed_responders);
            updatePreview();
        }

        restoreDraft();

        storyEditor.addEventListener('input', function () {
            persistDraft();
            updatePreview();
        });
        storyEditor.addEventListener('change', function () {
            persistDraft();
            updatePreview();
        });
        storyEditor.addEventListener('submit', function () {
            try {
                window.sessionStorage.setItem(storyDraftSubmittedKey, 'true');
            } catch (error) {
                return;
            }
        });

        if (clearDraftButton) {
            clearDraftButton.addEventListener('click', function () {
                removeStorageItem(storyDraftStorageKey);
                cleanupPreviewObjectUrl();
                storyEditor.reset();
                updatePreview();
            });
        }
    }

    syncPopupPreferenceWithPermission();
    updateSoundToggle();
    updatePopupToggle();
    setupStoryEditor();
    if (soundToggle) {
        soundToggle.addEventListener('click', handleSoundToggleClick);
    }
    if (popupToggle) {
        popupToggle.addEventListener('click', handlePopupToggleClick);
    }
    showPendingBrowserPopups();
    playPendingNotifications();
})();
