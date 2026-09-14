// 容灾备份 hook：写工具（edit/write/ast_edit/rename_file）执行成功后自动 git commit 快照。
// 发现机制：项目级 <cwd>/.omp/hooks/pre/*.ts（hookCapability），会话启动时加载。
// 注意：用 tool_result（post-execution）而非 tool_call——tool_call 是执行前拦截，此时工作区
// 尚无改动，status --porcelain 恒为空，快照永远提交不到本次更改（实测验证）。
// 只处理位于 git 仓库内的目标路径；任何异常静默吞掉，绝不阻断/影响工具结果（handler 抛错会 fail-closed）。
import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";
import { existsSync } from "node:fs";
import { isAbsolute, join, dirname } from "node:path";

const WRITE_TOOLS = new Set(["edit", "write", "ast_edit", "rename_file"]);

// 从目标路径向上逐级找 .git（含目标本身所在目录），返回仓库根目录或 null。
function findGitRoot(start: string): string | null {
  let dir = start;
  for (;;) {
    if (existsSync(join(dir, ".git"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

export default function backupHook(pi: HookAPI): void {
  pi.on("tool_result", async (event, ctx) => {
    if (!WRITE_TOOLS.has(event.toolName)) return;
    if (event.isError) return;
    try {
      const input = (event.input ?? {}) as Record<string, unknown>;
      const cwd = ctx.cwd ?? process.cwd();

      // 收集目标路径：edit/write 用 path；ast_edit 用 paths[]；lsp rename_file 用 file；另有 newPath/oldPath 兼容。
      const candidates: string[] = [];
      if (typeof input.path === "string") candidates.push(input.path);
      if (typeof input.file === "string") candidates.push(input.file);
      if (typeof input.newPath === "string") candidates.push(input.newPath);
      if (typeof input.oldPath === "string") candidates.push(input.oldPath);
      if (Array.isArray(input.paths)) {
        for (const p of input.paths) if (typeof p === "string") candidates.push(p);
      }
      if (candidates.length === 0) candidates.push(cwd);

      // 去重仓库根，逐仓库快照（git status 返回结构字段名实测为 code/stdout/stderr）。
      const repos = new Set<string>();
      for (const p of candidates) {
        const abs = isAbsolute(p) ? p : join(cwd, p);
        const repo = findGitRoot(abs);
        if (repo) repos.add(repo);
      }

      for (const repo of repos) {
        const status = await pi.exec("git", ["-C", repo, "status", "--porcelain"]);
        if (status.code !== 0 || !status.stdout.trim()) continue;
        await pi.exec("git", ["-C", repo, "add", "-A"]);
        await pi.exec("git", [
          "-C",
          repo,
          "commit",
          "-m",
          `snapshot after ${event.toolName} (${new Date().toISOString()})`,
        ]);
      }
    } catch (err) {
      // 静默：hook 失败绝不影响工具执行与结果。
      try {
        pi.logger?.error?.(`[backup hook] ${String(err)}`);
      } catch {
        /* ignore */
      }
    }
  });
}
