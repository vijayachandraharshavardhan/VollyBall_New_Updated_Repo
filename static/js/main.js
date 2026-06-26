/**
 * Volleyball Live Scorer - JavaScript
 * Real-time polling or WebSocket logic for viewers
 */

// Configuration
const CONFIG = {
    POLL_INTERVAL: 2000, // Poll every 2 seconds
    USE_WEBSOCKET: false, // Set to true to use WebSocket instead of polling
    API_BASE: '/api'
};

// State management
const state = {
    currentMatch: null,
    currentSet: null,
    scores: {
        teamA: 0,
        teamB: 0
    },
    sets: []
};

/**
 * Initialize the application
 */
function initApp() {
    console.log('Initializing Volleyball Scorer App');
    
    // Bind event listeners
    bindEventListeners();
    
    // Start real-time updates
    if (CONFIG.USE_WEBSOCKET) {
        initWebSocket();
    } else {
        startPolling();
    }
}

/**
 * Bind all event listeners
 */
function bindEventListeners() {
    // Score buttons
    const scoreButtons = document.querySelectorAll('.btn-score');
    scoreButtons.forEach(btn => {
        btn.addEventListener('click', handleScoreClick);
    });

    // Only bind undo/end-set if the page uses main.js for scoring (viewers page)
    const undoBtn = document.querySelector('.btn-undo[data-main]');
    if (undoBtn) {
        undoBtn.addEventListener('click', handleUndo);
    }

    const endSetBtn = document.querySelector('.btn-end-set[data-main]');
    if (endSetBtn) {
        endSetBtn.addEventListener('click', handleEndSet);
    }
}

/**
 * Handle score button clicks
 */
function handleScoreClick(event) {
    const team = event.target.dataset.team;
    const points = parseInt(event.target.dataset.points) || 1;
    
    updateScore(team, points);
}

/**
 * Update score and send to server
 */
async function updateScore(team, points) {
    if (!state.currentSet) {
        showAlert('No active set', 'warning');
        return;
    }

    // Update local state
    state.scores[team] += points;
    
    // Update UI
    updateScoreDisplay();
    
    // Send to server
    try {
        await sendScoreUpdate({
            setId: state.currentSet.id,
            team: team,
            points: points
        });
        
        showAlert(`Point awarded to ${team}`, 'success');
    } catch (error) {
        console.error('Error updating score:', error);
        showAlert('Failed to update score', 'danger');
    }
}

/**
 * Update score display on page
 */
function updateScoreDisplay() {
    const teamADisplay = document.querySelector('[data-display="teamA"]');
    const teamBDisplay = document.querySelector('[data-display="teamB"]');
    
    if (teamADisplay) {
        teamADisplay.textContent = state.scores.teamA;
        teamADisplay.classList.add('score-flip');
        setTimeout(() => teamADisplay.classList.remove('score-flip'), 600);
    }
    
    if (teamBDisplay) {
        teamBDisplay.textContent = state.scores.teamB;
        teamBDisplay.classList.add('score-flip');
        setTimeout(() => teamBDisplay.classList.remove('score-flip'), 600);
    }
}

/**
 * Handle undo operation
 */
async function handleUndo() {
    if (!state.currentSet) return;

    try {
        const response = await fetch(`${CONFIG.API_BASE}/undo-point`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ setId: state.currentSet.id })
        });

        const data = await response.json();
        if (data.status === 'success') {
            state.scores = data.scores;
            updateScoreDisplay();
            showAlert('Point undone', 'success');
        }
    } catch (error) {
        console.error('Error undoing point:', error);
        showAlert('Failed to undo point', 'danger');
    }
}

/**
 * Handle end set operation
 */
async function handleEndSet() {
    if (!state.currentSet) return;

    try {
        const response = await fetch(`${CONFIG.API_BASE}/end-set`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                setId: state.currentSet.id,
                scores: state.scores
            })
        });

        const data = await response.json();
        if (data.status === 'success') {
            state.sets.push(data.set);
            resetSetScores();
            loadCurrentSet();
            showAlert('Set ended', 'success');
        }
    } catch (error) {
        console.error('Error ending set:', error);
        showAlert('Failed to end set', 'danger');
    }
}

/**
 * Send score update to server
 */
async function sendScoreUpdate(data) {
    const response = await fetch(`${CONFIG.API_BASE}/score-update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
}

/**
 * Reset set scores
 */
function resetSetScores() {
    state.scores = {
        teamA: 0,
        teamB: 0
    };
    updateScoreDisplay();
}

/**
 * Load current set data
 */
async function loadCurrentSet() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/current-set`);
        const data = await response.json();
        
        if (data.set) {
            state.currentSet = data.set;
            state.scores = {
                teamA: data.set.teamAScore,
                teamB: data.set.teamBScore
            };
            updateScoreDisplay();
        }
    } catch (error) {
        console.error('Error loading current set:', error);
    }
}

/**
 * Start polling for updates (viewers page)
 */
function startPolling() {
    console.log('Starting polling for updates...');
    
    // Initial load
    pollForUpdates();
    
    // Poll every interval
    setInterval(pollForUpdates, CONFIG.POLL_INTERVAL);
}

/**
 * Poll for score updates
 */
async function pollForUpdates() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/score-updates`);
        const data = await response.json();
        
        if (data.updates) {
            updateViewerDisplay(data.updates);
        }
    } catch (error) {
        console.error('Error polling for updates:', error);
    }
}

/**
 * Update viewer display with latest scores
 */
function updateViewerDisplay(updates) {
    const scoreContainers = document.querySelectorAll('[data-viewer-match]');
    
    scoreContainers.forEach(container => {
        const matchId = container.dataset.viewerMatch;
        const matchData = updates[matchId];
        
        if (matchData) {
            const teamAScore = container.querySelector('[data-team="A"] .score');
            const teamBScore = container.querySelector('[data-team="B"] .score');
            
            if (teamAScore) {
                teamAScore.textContent = matchData.teamAScore;
                teamAScore.classList.add('score-flip');
                setTimeout(() => teamAScore.classList.remove('score-flip'), 600);
            }
            
            if (teamBScore) {
                teamBScore.textContent = matchData.teamBScore;
                teamBScore.classList.add('score-flip');
                setTimeout(() => teamBScore.classList.remove('score-flip'), 600);
            }
        }
    });
}

/**
 * Initialize WebSocket connection (optional)
 */
function initWebSocket() {
    console.log('Initializing WebSocket connection...');
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/scores`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateViewerDisplay(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Fallback to polling
        CONFIG.USE_WEBSOCKET = false;
        startPolling();
    };
}

/**
 * Show alert/notification
 */
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container') || document.body;
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-remove alert after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

/**
 * Format time in mm:ss format
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Animate score flip
 */
function animateScoreFlip(element) {
    element.classList.add('score-flip');
    setTimeout(() => element.classList.remove('score-flip'), 600);
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only run on pages that use data-viewer-match (not viewers page which has inline JS)
    if (document.querySelector('[data-viewer-match]')) {
        initApp();
    }
});
