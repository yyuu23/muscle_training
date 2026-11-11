import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles/global.css'

function App() {
  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1>私人健身教练 Agent</h1>
      <p>Phase 1: Engineering Foundation - Frontend stub created</p>
      <p>TODO: Implement full application structure in Phase 2+</p>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
