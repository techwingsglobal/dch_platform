document.addEventListener("DOMContentLoaded", function() {
    const sendButton = document.getElementById("send-btn");
    const voiceButton = document.getElementById("voice-btn");
    sendButton.addEventListener("click", () => sendMessage(false));
    voiceButton.addEventListener("click", startListening);

    function displayMessage(text, role) {
        const chatBox = document.getElementById("chat-box");
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${role}`;
        messageDiv.textContent = text;
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }


    function sendMessage(useVoice) {
        const input = document.getElementById("user-input");
        const userText = input.value.trim();
        if (!userText) return;
        displayMessage(userText, 'user');
        input.value = '';

        // Stop any ongoing speech when sending a new message
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
        }

        fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({message: userText, voice: useVoice})
        })
        .then(response => response.json())
        .then(data => {
            displayMessage(data.response, 'bot');
            if (data.voice) {
                speak(data.response);
            }
        });
    }

    function startListening() {
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel(); // Cancel any ongoing speech when starting to listen
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.start();

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById("user-input").value = transcript; // Display the recognized text in the input field
            sendMessage(true); // Send message with voice response
        }
    }

    function speak(text) {
        const synth = window.speechSynthesis;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.onend = function(event) {
            console.log('SpeechSynthesisUtterance.onend');
        }
        utterance.onerror = function(event) {
            console.error('SpeechSynthesisUtterance.onerror');
        }
        synth.speak(utterance);
    }
});
