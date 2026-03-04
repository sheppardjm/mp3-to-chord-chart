import './style.css'

document.querySelector('#app').innerHTML = `
  <h1>dontCave</h1>
  <p id="status">Checking backend...</p>
`

fetch('/api/health')
  .then(r => r.json())
  .then(data => {
    document.querySelector('#status').textContent =
      `Backend: ${data.status}`
  })
  .catch(err => {
    document.querySelector('#status').textContent =
      `Backend: unreachable (${err.message})`
  })
