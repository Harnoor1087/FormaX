import * as pdfjs from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import mammoth from 'mammoth/mammoth.browser';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export const MAX_FILE_MB = 10;

// Normalises whitespace and repairs line-break artefacts common in PDFs.
export function cleanText(raw) {
  return raw
    .replace(/\r\n?/g, '\n')
    .replace(/-\n(?=[a-z])/g, '')   // re-join words hyphenated across lines
    .replace(/[ \t]+/g, ' ')
    .replace(/ ?\n ?/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

async function pdfToText(buffer) {
  const pdf = await pdfjs.getDocument({ data: buffer }).promise;
  const pages = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const content = await (await pdf.getPage(i)).getTextContent();
    pages.push(content.items.map((it) => it.str + (it.hasEOL ? '\n' : ' ')).join(''));
  }
  return pages.join('\n\n');
}

export async function extractText(file) {
  if (file.size > MAX_FILE_MB * 1024 * 1024) {
    throw new Error(`File is larger than ${MAX_FILE_MB} MB. Upload a smaller file or paste the text.`);
  }
  const ext = file.name.split('.').pop().toLowerCase();
  let raw;
  if (ext === 'txt') raw = await file.text();
  else if (ext === 'pdf') raw = await pdfToText(await file.arrayBuffer());
  else if (ext === 'docx') raw = (await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() })).value;
  else throw new Error('Unsupported file type. Upload a PDF, DOCX or TXT file.');

  const text = cleanText(raw);
  if (!text) throw new Error('No readable text found. Scanned PDFs need OCR, which is not supported yet. Paste the text instead.');
  return text;
}
