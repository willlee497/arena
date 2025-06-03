<template>
  <div class="chat-container">
    <div class="upload-section">
      <h3>🤖 AI Flight Data Chatbot</h3>
      <p class="chat-subtitle">Upload your flight log to chat with AI about anomalies, performance, and analysis</p>
      <div class="upload-area" @drop="handleDrop" @dragover.prevent @dragenter.prevent>
        <input
          type="file"
          @change="upload"
          accept=".bin,.tlog"
          ref="fileInput"
          style="display: none"
        />
        <div class="upload-content" @click="$refs.fileInput.click()">
          <div v-if="!uploading && !sid">
            🤖 Drop flight log here to start AI chat analysis
          </div>
          <div v-else-if="uploading">
            🤖 AI is analyzing your flight data...
          </div>
          <div v-else class="upload-success">
            ✅ Ready for AI chat - Session: {{ sid.substring(0, 8) }}...
          </div>
        </div>
      </div>
    </div>

    <div v-if="sid" class="chat-section">
      <div class="suggested-questions" v-if="msgs.length === 0">
        <h4>💡 Try asking:</h4>
        <button
          v-for="q in suggestedQuestions"
          :key="q"
          @click="askSuggested(q)"
          class="suggestion-btn"
        >
          {{ q }}
        </button>
      </div>

      <div class="messages" ref="messages">
        <div
          v-for="m in msgs"
          :key="m.id"
          :class="['message', m.role]"
        >
          <div class="message-content">
            <div class="message-text" v-html="formatMessage(m.content)"></div>
            <div class="message-time">{{ formatTime(m.timestamp) }}</div>
          </div>
        </div>
        <div v-if="isTyping" class="message assistant typing">
          <div class="message-content">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <form @submit.prevent="ask" class="input-form">
        <input
          v-model="text"
          placeholder="Ask about flight anomalies, GPS issues, battery performance..."
          :disabled="isTyping"
          class="message-input"
        />
        <button type="submit" :disabled="isTyping || !text.trim()" class="send-btn">
          {{ isTyping ? '⏳' : '➤' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
    name: 'ChatPanel',
    data () {
        return {
            sid: null,
            msgs: [],
            text: '',
            uploading: false,
            isTyping: false,
            suggestedQuestions: [
                'Are there any anomalies in this flight?',
                'Can you spot any issues in the GPS data?',
                'What was the highest altitude reached?',
                'How was the battery performance?',
                'Were there any control system problems?',
                'What was the total flight time?'
            ]
        }
    },
    methods: {
        handleDrop (e) {
            e.preventDefault()
            const files = e.dataTransfer.files
            if (files.length > 0) {
                this.uploadFile(files[0])
            }
        },
        async upload (e) {
            this.uploadFile(e.target.files[0])
        },
        async uploadFile (file) {
            if (!file) return

            this.uploading = true
            try {
                const fd = new FormData()
                fd.append('file', file)
                const res = await fetch('http://127.0.0.1:8000/upload-log', {
                    method: 'POST',
                    body: fd
                })

                if (!res.ok) throw new Error('Upload failed')

                const data = await res.json()
                this.sid = data.session_id

                // Add welcome message
                this.msgs.push({
                    id: Date.now(),
                    role: 'assistant',
                    content: 'Flight data loaded successfully! ' +
                        `I've analyzed your flight log and detected ${data.rows} data points. ` +
                        'I\'m ready to answer questions about flight anomalies, GPS quality, ' +
                        'battery performance, and more.',
                    timestamp: new Date()
                })
            } catch (error) {
                alert('Failed to upload file: ' + error.message)
            } finally {
                this.uploading = false
            }
        },
        askSuggested (question) {
            this.text = question
            this.ask()
        },
        async ask () {
            if (!this.text.trim() || this.isTyping) return

            const userMessage = {
                id: Date.now(),
                role: 'user',
                content: this.text,
                timestamp: new Date()
            }
            this.msgs.push(userMessage)

            const assistantMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: '',
                timestamp: new Date()
            }
            this.msgs.push(assistantMessage)

            const userText = this.text
            this.text = ''
            this.isTyping = true

            try {
                const response = await fetch(`http://127.0.0.1:8000/chat/${this.sid}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: userText })
                })

                if (!response.ok) throw new Error('Chat request failed')

                const reader = response.body.getReader()
                const decoder = new TextDecoder()

                while (true) {
                    const { done, value } = await reader.read()
                    if (done) break

                    const chunk = decoder.decode(value)
                    const lines = chunk.split('\n')

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6)
                            if (data.trim()) {
                                assistantMessage.content += data
                                this.$nextTick(() => {
                                    this.scrollToBottom()
                                })
                            }
                        }
                    }
                }
            } catch (error) {
                assistantMessage.content = 'Sorry, I encountered an error processing your request.'
            } finally {
                this.isTyping = false
                this.$nextTick(() => {
                    this.scrollToBottom()
                })
            }
        },
        formatMessage (content) {
            // Convert markdown-like formatting to HTML
            return content
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>')
        },
        formatTime (timestamp) {
            return timestamp.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit'
            })
        },
        scrollToBottom () {
            if (this.$refs.messages) {
                this.$refs.messages.scrollTop = this.$refs.messages.scrollHeight
            }
        }
    },
    watch: {
        msgs: {
            handler () {
                this.$nextTick(() => {
                    this.scrollToBottom()
                })
            },
            deep: true
        }
    }
}
</script>

<style scoped>
.chat-container {
    max-width: 800px;
    margin: 20px auto;
    background: #f8f9fa;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    overflow: hidden;
}

.upload-section {
    padding: 24px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.upload-section h3 {
    margin: 0 0 16px 0;
    font-size: 24px;
    font-weight: 600;
}

.upload-section p {
    margin: 0 0 16px 0;
    font-size: 14px;
    font-weight: 500;
}

.upload-area {
    border: 2px dashed rgba(255,255,255,0.3);
    border-radius: 8px;
    padding: 24px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
}

.upload-area:hover {
    border-color: rgba(255,255,255,0.6);
    background: rgba(255,255,255,0.1);
}

.upload-content {
    font-size: 16px;
    font-weight: 500;
}

.upload-success {
    color: #90EE90;
}

.chat-section {
    display: flex;
    flex-direction: column;
    height: 600px;
}

.suggested-questions {
    padding: 20px;
    border-bottom: 1px solid #e9ecef;
}

.suggested-questions h4 {
    margin: 0 0 12px 0;
    color: #495057;
    font-size: 14px;
    font-weight: 600;
}

.suggestion-btn {
    display: inline-block;
    margin: 4px 8px 4px 0;
    padding: 8px 12px;
    background: #e9ecef;
    border: none;
    border-radius: 20px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.suggestion-btn:hover {
    background: #667eea;
    color: white;
}

.messages {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
    background: white;
}

.message {
    margin-bottom: 16px;
    display: flex;
}

.message.user {
    justify-content: flex-end;
}

.message.assistant {
    justify-content: flex-start;
}

.message-content {
    max-width: 70%;
    padding: 12px 16px;
    border-radius: 18px;
    position: relative;
}

.user .message-content {
    background: #667eea;
    color: white;
    border-bottom-right-radius: 4px;
}

.assistant .message-content {
    background: #f1f3f4;
    color: #333;
    border-bottom-left-radius: 4px;
}

.message-text {
    line-height: 1.4;
    word-wrap: break-word;
}

.message-time {
    font-size: 10px;
    opacity: 0.7;
    margin-top: 4px;
}

.typing-indicator {
    display: flex;
    align-items: center;
    gap: 4px;
}

.typing-indicator span {
    height: 8px;
    width: 8px;
    border-radius: 50%;
    background: #999;
    animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-10px); }
}

.input-form {
    display: flex;
    padding: 20px;
    background: #f8f9fa;
    border-top: 1px solid #e9ecef;
}

.message-input {
    flex: 1;
    padding: 12px 16px;
    border: 1px solid #ddd;
    border-radius: 24px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s ease;
}

.message-input:focus {
    border-color: #667eea;
}

.send-btn {
    margin-left: 12px;
    padding: 12px 20px;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 24px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s ease;
}

.send-btn:hover:not(:disabled) {
    background: #5a6fd8;
    transform: translateY(-1px);
}

.send-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
</style>
