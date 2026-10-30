const fs = require("node:fs");
const file = fs.readFileSync("docs/index.html", "utf8");
const opening = (file.match(/<script(?:\s[^>]*)?>/gi) || []).length;
const closing = (file.match(/<\/script\s*>/gi) || []).length;
const htmlOpen = (file.match(/<html(?:\s[^>]*)?>/gi) || []).length;
const htmlClose = (file.match(/<\/html\s*>/gi) || []).length;
if (opening !== 1 || closing !== 1) throw new Error("Expected exactly one script block, found " + opening + " opening and " + closing + " closing tags");
if (htmlOpen !== 1 || htmlClose !== 1) throw new Error("Expected exactly one complete HTML document");
if (!/<\/html\s*>\s*$/i.test(file)) throw new Error("Stray content after </html>: possible duplicated script displayed as webpage text");
const block = file.match(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script\s*>/i);
if (!block) throw new Error("Frontend JavaScript not found");
new Function(block[1]);
for (const id of ["coverage","top","listCount","search","table","news","refresh","status","detail","trOnly"]) {
  if (!file.includes('id="'+id+'"')) throw new Error("Missing UI element: " + id);
}
console.log("Frontend verified: single script, complete HTML, no trailing source, required controls present.");
