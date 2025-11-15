/**
 * Copy to clipboard functionality for code blocks
 */

document.addEventListener('DOMContentLoaded', () => {
  // Add click handlers to all copy buttons
  const copyButtons = document.querySelectorAll('.copy-button');

  copyButtons.forEach(button => {
    button.addEventListener('click', async () => {
      const textToCopy = button.getAttribute('data-copy');

      try {
        await navigator.clipboard.writeText(textToCopy);

        // Visual feedback
        const originalHTML = button.innerHTML;
        button.innerHTML = `
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
          </svg>
        `;
        button.classList.add('btn-success');

        // Reset after 2 seconds
        setTimeout(() => {
          button.innerHTML = originalHTML;
          button.classList.remove('btn-success');
        }, 2000);
      } catch (err) {
        console.error('Failed to copy text:', err);
      }
    });
  });
});
