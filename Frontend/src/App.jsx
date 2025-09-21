import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Calendar from 'react-calendar';
import 'react-calendar/dist/Calendar.css';
import './App.css';

const API_URL = 'http://127.0.0.1:8000/chat';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messageListRef = useRef(null);

  useEffect(() => {
    const initialSessionId = `session_${Date.now()}`;
    setSessionId(initialSessionId);
    setMessages([{ 
      type: 'text',
      sender: 'ai', 
      text: 'Hello! I am Schedura AI. How can I help you book an appointment today?' 
    }]);
  }, []);

  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (messageText, currentMessages) => {
    if (!messageText.trim()) return;

    const userMessage = { type: 'text', sender: 'user', text: messageText };
    const newMessages = [...currentMessages, userMessage];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const response = await axios.post(API_URL, {
        messages: newMessages.map(({sender, text}) => ({sender, text})),
        session_id: sessionId,
      });

      const aiMessage = { sender: 'ai', ...response.data };
      setMessages(prev => [...prev, aiMessage]);

    } catch (error) {
      console.error('Error fetching response:', error);
      const errorMessage = { type: 'text', sender: 'ai', text: 'Sorry, I encountered an error. Please try again.' };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input, messages);
    setInput('');
  };

  const handleOptionClick = (optionText) => {
    sendMessage(optionText, messages);
  };
  
  const handleDateChange = (date) => {
    const formattedDate = date.toISOString().split('T')[0];
    sendMessage(`Check availability for ${formattedDate}`, messages);
  };

  const renderMessageContent = (msg) => {
    switch (msg.type) {
      case 'service_options':
        // --- ADD THIS CHECK ---
        if (msg.data && msg.data[0]?.error) {
          return <p>Sorry, I couldn't fetch the services right now. Error: {msg.data[0].error}</p>;
        }
        return (
          <>
            <p>{msg.text}</p>
            <div className="options-container">
              {msg.data.map((service, i) => (
                <button key={i} className="option-button" onClick={() => handleOptionClick(`I'd like to book the ${service.name}`)}>
                  <strong>{service.name}</strong>
                  <span>{service.price}</span>
                </button>
              ))}
            </div>
          </>
        );
      case 'slot_options':
        // --- ADD THIS CHECK ---
        if (msg.data && msg.data[0]?.error) {
          return <p>Sorry, I couldn't fetch time slots. Error: {msg.data[0].error}</p>;
        }
        return (
          <>
            <p>{msg.text}</p>
            <div className="options-container-grid">
              {msg.data.map((slot, i) => (
                <button key={i} className="option-button-slot" onClick={() => handleOptionClick(`Book me for ${slot}`)}>
                  {slot}
                </button>
              ))}
            </div>
          </>
        );
      case 'date_request':
        return (
          <>
            <p>{msg.text}</p>
            <div className="calendar-container">
              <Calendar
                onChange={handleDateChange}
                value={new Date()}
                minDate={new Date()}
              />
            </div>
          </>
        );
      default: // 'text' type
        return <p>{msg.text}</p>;
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header"><h1>Schedura AI</h1></div>
      <div className="message-list" ref={messageListRef}>
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            {renderMessageContent(msg)}
          </div>
        ))}
        {isLoading && <div className="loading-indicator">Schedura is thinking...</div>}
      </div>
      <form onSubmit={handleSubmit} className="input-form">
        <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type your message..." disabled={isLoading} />
        <button type="submit" disabled={isLoading}>Send</button>
      </form>
    </div>
  );
}

export default App;