document.addEventListener("DOMContentLoaded", () => {
    // Check Health
    fetch('/api/health')
        .then(r => r.json())
        .then(data => {
            document.getElementById('health-status').innerText = `Backend: ${data.status} | Neo4j: ${data.neo4j}`;
        })
        .catch(err => {
            document.getElementById('health-status').innerText = 'Error connecting to API';
        });

    // Run Pipeline
    document.getElementById('run-pipeline-btn').addEventListener('click', () => {
        const target = document.getElementById('target-input').value;
        const statusDiv = document.getElementById('pipeline-status');
        const outputPre = document.getElementById('pipeline-output');
        
        statusDiv.innerText = 'Running analysis...';
        outputPre.innerText = '';
        
        fetch('/api/analyze/full', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_company: target })
        })
        .then(r => r.json())
        .then(data => {
            statusDiv.innerText = 'Analysis Complete';
            outputPre.innerText = JSON.stringify(data, null, 2);
        })
        .catch(err => {
            statusDiv.innerText = 'Error';
            outputPre.innerText = String(err);
        });
    });
});
