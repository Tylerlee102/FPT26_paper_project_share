import fs from "node:fs/promises";
import { pathToFileURL } from "node:url";

const [inputPath, outputDir, artifactToolPath] = process.argv.slice(2);
if (!inputPath || !outputDir || !artifactToolPath) {
  throw new Error(
    "usage: node inspect_reviewer_workbook.mjs <input.xlsx> <output-dir> <artifact-tool.mjs>",
  );
}

const { FileBlob, SpreadsheetFile } = await import(
  pathToFileURL(artifactToolPath).href
);
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

await fs.mkdir(outputDir, { recursive: true });
const summary = await workbook.inspect({
  kind: "workbook,sheet,table,thread,drawing",
  maxChars: 20000,
  tableMaxRows: 10,
  tableMaxCols: 12,
  tableMaxCellChars: 160,
});
const summaryPayload =
  typeof summary === "string" ? summary : JSON.stringify(summary, null, 2);
await fs.writeFile(`${outputDir}/summary.json`, summaryPayload, "utf8");

const commentsSheet = workbook.worksheets.getItem("Comments");
const usedRange = commentsSheet.getUsedRange(true);
const values = usedRange.values;
await fs.writeFile(
  `${outputDir}/comments_values.json`,
  JSON.stringify({ address: usedRange.address, values }, null, 2),
  "utf8",
);

const preview = await workbook.render({
  sheetName: "Comments",
  autoCrop: "all",
  scale: 0.75,
  format: "png",
});
await fs.writeFile(
  `${outputDir}/comments_preview.png`,
  new Uint8Array(await preview.arrayBuffer()),
);

console.log(
  JSON.stringify(
    {
      usedRange: usedRange.address,
      rowCount: values.length,
      columnCount: values[0]?.length ?? 0,
      values: `${outputDir}/comments_values.json`,
      preview: `${outputDir}/comments_preview.png`,
    },
    null,
    2,
  ),
);
