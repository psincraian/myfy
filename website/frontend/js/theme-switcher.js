/**
 * Theme switcher for DaisyUI
 * Handles light/dark mode with localStorage persistence
 */

const STORAGE_KEY = 'myfy-theme-preference'
const LIGHT_THEME = 'light'
const DARK_THEME = 'dark'

function getSystemPreference() {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return DARK_THEME
  }
  return LIGHT_THEME
}

function getCurrentTheme() {
  const saved = localStorage.getItem(STORAGE_KEY)
  return saved || getSystemPreference()
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem(STORAGE_KEY, theme)
  updateThemeIcons(theme)
}

function toggleTheme() {
  const current = getCurrentTheme()
  const next = current === LIGHT_THEME ? DARK_THEME : LIGHT_THEME
  setTheme(next)
}

function updateThemeIcons(theme) {
  const sunIcons = document.querySelectorAll('.theme-icon-sun')
  const moonIcons = document.querySelectorAll('.theme-icon-moon')

  if (theme === DARK_THEME) {
    sunIcons.forEach(icon => icon.classList.remove('hidden'))
    moonIcons.forEach(icon => icon.classList.add('hidden'))
  } else {
    sunIcons.forEach(icon => icon.classList.add('hidden'))
    moonIcons.forEach(icon => icon.classList.remove('hidden'))
  }
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', () => {
  const theme = getCurrentTheme()
  setTheme(theme)

  // Add click handlers to theme toggle buttons
  document.querySelectorAll('[data-theme-toggle]').forEach(button => {
    button.addEventListener('click', toggleTheme)
  })
})

// Apply theme immediately (before DOMContentLoaded to prevent flash)
;(function() {
  const theme = getCurrentTheme()
  document.documentElement.setAttribute('data-theme', theme)
})()
