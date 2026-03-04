import './style.css'
import { renderChart } from './renderChart.js'

document.querySelector('#app').innerHTML = `
  <h1>dontCave</h1>
  <form id="upload-form">
    <label for="file-input">Select MP3 file:</label>
    <input type="file" id="file-input" accept=".mp3,audio/mpeg" required />
    <label for="lyrics">Paste lyrics (blank lines separate sections):</label>
    <textarea id="lyrics" rows="20" cols="60" placeholder="Paste lyrics here. Use blank lines to separate sections (verse, chorus, etc)."></textarea>
    <button type="submit" id="submit-btn">Analyze</button>
  </form>
  <p id="status"></p>
  <div id="chord-chart"></div>
`

const form = document.querySelector('#upload-form')
const fileInput = document.querySelector('#file-input')
const statusEl = document.querySelector('#status')
const chartEl = document.querySelector('#chord-chart')
const submitBtn = document.querySelector('#submit-btn')

form.addEventListener('submit', async (e) => {
  e.preventDefault()

  chartEl.innerHTML = ''

  if (!fileInput.files.length) {
    statusEl.textContent = 'Please select an MP3 file.'
    return
  }

  const formData = new FormData()
  formData.append('file', fileInput.files[0])
  formData.append('lyrics', document.querySelector('#lyrics').value)

  statusEl.textContent = 'Analyzing audio...'
  submitBtn.disabled = true

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }))
      statusEl.textContent = `Error: ${err.detail || response.statusText}`
      return
    }

    const data = await response.json()
    statusEl.textContent = 'Analysis complete.'
    renderChart(data, chartEl)
  } catch (err) {
    statusEl.textContent = `Network error: ${err.message}`
  } finally {
    submitBtn.disabled = false
  }
})
