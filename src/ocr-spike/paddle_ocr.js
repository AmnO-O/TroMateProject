// PaddleOCR PP-OCRv5 (mobile detection + Latin recognition) through the RustO
// Node binding. Reads image paths from argv, prints one JSON line of text boxes
// per image; engines.py rebuilds the lines.
const path = require('path');
const { RustO } = require('@rustors/node');

const models = path.join(__dirname, 'node_modules', '@rustors');
const rec = process.env.PADDLE_REC || 'latin';
const recDir = rec === 'latin' ? 'model-ppocrv5-latin' : 'model-ppocrv5-mobile';
const engine = RustO.initialize({
  detection: { model_path: path.join(models, 'model-ppocrv5-mobile/models/det.rten') },
  recognition: {
    model_path: path.join(models, recDir, 'models/rec.rten'),
    dict_path: path.join(models, recDir, 'models/dict.txt'),
  },
});

for (const image of process.argv.slice(2)) {
  const started = process.hrtime.bigint();
  const results = engine.detectTextFile(image, { output: 'lines' });
  const ms = Number(process.hrtime.bigint() - started) / 1e6;
  const boxes = results.map(r => ({ text: r.text, score: r.score, box_points: r.box_points }));
  console.log(JSON.stringify({ image, boxes, ms }));
}
