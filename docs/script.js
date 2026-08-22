document.querySelectorAll('pre').forEach((pre) => {

    const button = document.createElement('button');
    button.innerText = 'Copy';
    button.className = 'copy-button';


    pre.style.position = 'relative';
    pre.appendChild(button);

    button.addEventListener('click', async () => {
        const code = pre.querySelector('code');
        const text = code.innerText;

        try {
            await navigator.clipboard.writeText(text);
            button.innerText = 'Copied!';
            button.classList.add('copied');

            setTimeout(() => {
                button.innerText = 'Copy';
                button.classList.remove('copied');
            }, 2000);
        } catch (err) {
            console.error('Failed to copy: ', err);
        }
    });
});

const mV = document.getElementById('mV')
const mH = document.getElementById('mH')
mV.addEventListener('click', () => {
    mH.style.display = mH.style.display === "none" ? "flex" : "none";
})