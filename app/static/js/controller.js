// Projection Controller - sends commands to the server

const client = new WSClient(SESSION_ID, 'controller', (msg) => {
    if (msg.type === 'state_sync' || msg.type === 'state_update') {
        updateControllerUI(msg.data);
    }
});

function sendCommand(action) {
    client.send({ action });
}

function sendText() {
    const text = document.getElementById('manual-text').value;
    client.send({ action: 'set_text', text });
}

function updateControllerUI(state) {
    document.getElementById('current-text').textContent = state.current_text || '等待中...';
    document.getElementById('current-text-secondary').textContent = state.current_text_secondary || '';
    document.getElementById('connection-status').textContent = '已連線';
}
