document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('scrapeForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = document.getElementById('btnLoader');
    const resultsSection = document.getElementById('resultsSection');
    const outputCode = document.getElementById('outputCode');
    const pageTitleTag = document.getElementById('pageTitle');
    const copyBtn = document.getElementById('copyBtn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const url = document.getElementById('urlInput').value;
        const extractMarkdown = document.getElementById('markdownToggle').checked;

        // UI Loading State
        submitBtn.disabled = true;
        btnText.textContent = 'Scraping...';
        btnLoader.classList.remove('hidden');
        resultsSection.classList.add('hidden');

        try {
            // Note: In production this would point to the deployed URL, here we use localhost
            const response = await fetch('http://127.0.0.1:8000/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    extract_markdown: extractMarkdown,
                    wait_for_timeout: 1500
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to scrape URL');
            }

            const data = await response.json();
            
            // Render Results
            outputCode.textContent = data.content;
            
            // Set language class for Prism
            outputCode.className = extractMarkdown ? 'language-markdown' : 'language-markup';
            Prism.highlightElement(outputCode);

            pageTitleTag.textContent = data.title || url;
            pageTitleTag.title = data.title || url;
            
            resultsSection.classList.remove('hidden');
            
            // Scroll to results smoothly
            setTimeout(() => {
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);

        } catch (error) {
            console.error('Scraping Error:', error);
            alert(`Error: ${error.message}`);
        } finally {
            // Reset UI State
            submitBtn.disabled = false;
            btnText.textContent = 'Extract Data';
            btnLoader.classList.add('hidden');
        }
    });

    // Copy to clipboard functionality
    copyBtn.addEventListener('click', () => {
        const textToCopy = outputCode.textContent;
        navigator.clipboard.writeText(textToCopy).then(() => {
            // Visual feedback
            const originalIcon = copyBtn.innerHTML;
            copyBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#27C93F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
            
            setTimeout(() => {
                copyBtn.innerHTML = originalIcon;
            }, 2000);
        });
    });
});
