#!/usr/bin/env node
/**
 * defuddle-extract.js
 *
 * Extracts main content from a URL using defuddle and outputs JSON to stdout.
 *
 * Usage: node scripts/defuddle-extract.js <url>
 *
 * Output JSON:
 * {
 *   "title": "Page Title",
 *   "author": "Author Name",
 *   "description": "Meta description",
 *   "published": "2024-01-15",
 *   "content": "# Markdown content...",
 *   "site": "Site Name",
 *   "domain": "example.com",
 *   "wordCount": 1234
 * }
 */

import { JSDOM } from 'jsdom';
import { Defuddle } from 'defuddle/node';

async function extractPage(url) {
    try {
        // Fetch the page with JSDOM
        const dom = await JSDOM.fromURL(url, {
            userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            referrer: url,
        });

        // Extract content with defuddle
        const result = await Defuddle(dom, url, {
            markdown: true,
        });

        // Output relevant fields as JSON
        const output = {
            title: result.title || null,
            author: result.author || null,
            description: result.description || null,
            published: result.published || null,
            content: result.content || '',
            site: result.site || null,
            domain: result.domain || null,
            wordCount: result.wordCount || 0,
        };

        console.log(JSON.stringify(output));
    } catch (error) {
        // Output error as JSON for Python to parse
        console.error(JSON.stringify({
            error: true,
            message: error.message,
            code: error.code || 'UNKNOWN',
        }));
        process.exit(1);
    }
}

// Get URL from command line
const url = process.argv[2];

if (!url) {
    console.error(JSON.stringify({
        error: true,
        message: 'Usage: node defuddle-extract.js <url>',
        code: 'MISSING_URL',
    }));
    process.exit(1);
}

// Validate URL
try {
    new URL(url);
} catch {
    console.error(JSON.stringify({
        error: true,
        message: `Invalid URL: ${url}`,
        code: 'INVALID_URL',
    }));
    process.exit(1);
}

extractPage(url);
