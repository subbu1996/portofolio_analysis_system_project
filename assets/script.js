document.addEventListener('keydown', function(event) {
    // Check if the target is the user-input textarea
    if (event.target.id === 'user-input') {
        // If Enter is pressed WITHOUT Shift
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // Prevent creating a new line
            
            // Find the send button and click it
            var sendBtn = document.getElementById('send-btn');
            if (sendBtn) {
                sendBtn.click();
            }
        }
    }
});