const fs = require("node:fs");
const file = fs.readFileSync("docs/index.html", "utf8");
const block = file.match(/<script>([\s\S]*?)<\/script>/i);
if (!block) { throw new Error("No frontend script found"); }
new Function(block[1]);
for (const id of ["coverage","top","listCount","search","table","news","refresh","status","detail"]) {
  if (!file.includes('id="'+id+'"')) throw new Error("Missing UI element: "+id);
}
console.log("Frontend script parsed, required controls present.");
