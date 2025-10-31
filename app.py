<!DOCTYPE html>
<html>
<head>
    <title>ChatBot GDE</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 0 auto; padding: 20px; }
        .chat-container { background: #f5f5f5; padding: 20px; border-radius: 10px; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .user-message { background: #007bff; color: white; text-align: right; }
        .bot-message { background: white; }
        input { width: 70%; padding: 8px; }
        button { padding: 8px 15px; background: #007bff; color: white; border: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="chat-container">
        <h2>🤖 ChatBot GDE</h2>
        <div id="chat-messages">
            <div class="message bot-message">¡Hola! Pregúntame sobre el sistema GDE.</div>
        </div>
        <div>
            <input type="text" id="user-input" placeholder="Escribe tu pregunta...">
            <button onclick="sendMessage()">Enviar</button>
        </div>
    </div>

    <script>
        function sendMessage() {
            const input = document.getElementById('user-input');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Agregar mensaje usuario
            const chat = document.getElementById('chat-messages');
            chat.innerHTML += `<div class="message user-message">${message}</div>`;
            input.value = '';
            
            // Enviar al servidor
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: message })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    chat.innerHTML += `<div class="message bot-message">${data.response}</div>`;
                } else {
                    chat.innerHTML += `<div class="message bot-message">❌ Error: ${data.error}</div>`;
                }
                chat.scrollTop = chat.scrollHeight;
            });
        }
        
        document.getElementById('user-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>