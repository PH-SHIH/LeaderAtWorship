// Projection Display - receives state updates and renders subtitles

const client = new WSClient(SESSION_ID, 'display', (msg) => {
    if (msg.type === 'state_sync' || msg.type === 'state_update') {
        updateDisplay(msg.data);
    }
});

function updateDisplay(state) {
    const textEl = document.getElementById('subtitle-text');
    const secondaryEl = document.getElementById('subtitle-text-secondary');
    const blankEl = document.getElementById('blank-overlay');

    textEl.textContent = state.current_text || '';
    secondaryEl.textContent = state.current_text_secondary || '';

    if (state.is_blank) {
        blankEl.classList.remove('hidden');
    } else {
        blankEl.classList.add('hidden');
    }
}
