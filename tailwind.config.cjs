/** Keep the defaults used by the site's Tailwind 3.4.17 CDN script. */
module.exports = {
    content: {
        files: [
            './nahiyas/*.html',
            './shrine_sites/*.html',
            './village_sites/*.html',
            './village_transcripts/*.html'
        ],
        // Scan class attributes and inline scripts, without treating the long
        // multilingual transcripts as possible CSS class names.
        transform: {
            html: source => [
                ...Array.from(source.matchAll(/\bclass\s*=\s*["']([^"']*)["']/g), match => match[1]),
                ...Array.from(source.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi), match => match[1])
            ].join('\n')
        }
    },
    theme: { extend: {} },
    plugins: []
};
