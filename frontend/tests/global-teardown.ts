/**
 * Playwright global teardown — cleans up auth artifacts.
 */
import * as fs from "fs";

export default async function globalTeardown() {
  try {
    fs.rmSync("playwright/.auth/token.txt", { force: true });
  } catch {
    // ignore
  }
}
