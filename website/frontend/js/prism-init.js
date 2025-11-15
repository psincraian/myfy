// Prism.js initialization for Python and Bash/Terminal syntax highlighting
import Prism from 'prismjs';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-bash';

// Manual highlighting mode - only highlight when explicitly called
Prism.manual = true;

// Highlight all code blocks on page load
document.addEventListener('DOMContentLoaded', () => {
  Prism.highlightAll();
});

export default Prism;
