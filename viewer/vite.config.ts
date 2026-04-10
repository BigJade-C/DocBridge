import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";

import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const execFileAsync = promisify(execFile);

function editorExportPlugin(): Plugin {
  const repoRoot = path.resolve(__dirname, "..");
  const pythonPath = path.join(repoRoot, "src");

  async function handleExport(request: Request, response: import("node:http").ServerResponse) {
    if (request.method !== "POST" || request.url !== "/api/export-docx") {
      return false;
    }

    const chunks: Buffer[] = [];
    for await (const chunk of request) {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }

    const payload = JSON.parse(Buffer.concat(chunks).toString("utf-8")) as {
      editorModel: object;
      originalIr?: object | null;
      fileName?: string;
    };

    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "docbridge-export-"));
    const editorModelPath = path.join(tempDir, "editor-model.json");
    const originalIrPath = path.join(tempDir, "original-ir.json");
    const outputPath = path.join(tempDir, "export.docx");

    try {
      await fs.writeFile(editorModelPath, JSON.stringify(payload.editorModel), "utf-8");
      if (payload.originalIr) {
        await fs.writeFile(originalIrPath, JSON.stringify(payload.originalIr), "utf-8");
      }

      const args = [
        "-m",
        "hwp_parser.editor_model.export_cli",
        editorModelPath,
        outputPath,
      ];
      if (payload.originalIr) {
        args.push("--original-ir-json", originalIrPath);
      }

      await execFileAsync("python3", args, {
        cwd: repoRoot,
        env: {
          ...process.env,
          PYTHONPATH: pythonPath,
        },
      });

      const fileBytes = await fs.readFile(outputPath);
      response.statusCode = 200;
      response.setHeader(
        "Content-Disposition",
        `attachment; filename="${payload.fileName ?? "editor-export.docx"}"`,
      );
      response.setHeader(
        "Content-Type",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      );
      response.end(fileBytes);
    } catch (error) {
      response.statusCode = 500;
      response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify({ error: error instanceof Error ? error.message : String(error) }));
    } finally {
      await fs.rm(tempDir, { recursive: true, force: true });
    }

    return true;
  }

  async function handleImport(request: Request, response: import("node:http").ServerResponse) {
    if (request.method !== "POST" || request.url !== "/api/import-document") {
      return false;
    }

    const chunks: Buffer[] = [];
    for await (const chunk of request) {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }

    const payload = JSON.parse(Buffer.concat(chunks).toString("utf-8")) as {
      fileName?: string;
      fileContentBase64?: string;
    };
    const fileName = path.basename(payload.fileName ?? "");
    const fileContentBase64 = payload.fileContentBase64 ?? "";
    const extension = path.extname(fileName).toLowerCase();

    if (!fileName || !fileContentBase64) {
      response.statusCode = 400;
      response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify({ error: "Import payload is incomplete." }));
      return true;
    }

    if (![".hwp", ".docx", ".hwpx"].includes(extension)) {
      response.statusCode = 400;
      response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify({ error: `Unsupported import format: ${extension || "unknown"}` }));
      return true;
    }

    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "docbridge-import-"));
    const inputPath = path.join(tempDir, fileName);
    const outputIrPath = path.join(tempDir, "imported.ir.json");

    try {
      await fs.writeFile(inputPath, Buffer.from(fileContentBase64, "base64"));

      await execFileAsync(
        "python3",
        [
          "-m",
          "hwp_parser.importers.cli",
          inputPath,
          outputIrPath,
          "--artifact-root",
          path.join(repoRoot, "artifacts", "imports"),
        ],
        {
          cwd: repoRoot,
          env: {
            ...process.env,
            PYTHONPATH: pythonPath,
          },
        },
      );

      const irPayload = await fs.readFile(outputIrPath, "utf-8");
      response.statusCode = 200;
      response.setHeader("Content-Type", "application/json");
      response.end(irPayload);
    } catch (error) {
      response.statusCode = 500;
      response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify({ error: error instanceof Error ? error.message : String(error) }));
    } finally {
      await fs.rm(tempDir, { recursive: true, force: true });
    }

    return true;
  }

  return {
    name: "docbridge-editor-export",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!(await handleExport(req, res)) && !(await handleImport(req, res))) {
          next();
        }
      });
    },
    configurePreviewServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!(await handleExport(req, res)) && !(await handleImport(req, res))) {
          next();
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), editorExportPlugin()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
