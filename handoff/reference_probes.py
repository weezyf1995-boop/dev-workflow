# DISPOSABLE: the adversarial probes run against reference_frozen_guard_v2.py and a push hook (dropped), prior art for the frozen tripwire tests of issue #16, until that ticket lands.
import json, os, pathlib, subprocess, tempfile
HERE = pathlib.Path(__file__).parent; TMP = pathlib.Path(tempfile.mkdtemp()); repo = TMP/"repo"; repo.mkdir()
home = TMP/"home"; home.mkdir(); env = dict(os.environ, HOME=str(home))
def run(a, cwd=repo): subprocess.run(a, cwd=cwd, capture_output=True, check=True)
run(["git","init","-q"]); run(["git","checkout","-qb","main"]); run(["git","config","user.email","t@t"]); run(["git","config","user.name","t"])
(repo/"payments.py").write_text("# FROZEN CORE: money\n"); (repo/"ui.py").write_text("x\n"); (repo/"notes.md").write_text("Mark with `# FROZEN CORE: <why>`\n")
(repo/"old").mkdir(); (repo/"old"/"payments.py").write_text("x=1\n"); (repo/"sub").mkdir(); (repo/"sub"/"risk.py").write_text("# FROZEN CORE: limits\n")
os.symlink(repo/"payments.py", repo/"link.py"); os.link(repo/"payments.py", TMP/"hard.py")
run(["git","add","-A"]); run(["git","commit","-qm","i"])
wt = repo/".claude"/"worktrees"/"t1"; run(["git","worktree","add","-q",str(wt),"-b","t1"])
def hook(s, payload):
    p = subprocess.run(["python3", str(HERE/s)], input=json.dumps(payload), capture_output=True, text=True, env=env)
    return p.returncode==0 and '"deny"' in p.stdout, p.stdout
fails=[]; n=0
def check(name, got, want):
    global n; n+=1; ok = got==want; print(("ok   " if ok else "FAIL ")+name+f" (denied={got})"); 
    if not ok: fails.append(name)
def edit(path, cwd=repo, tool="Edit"): return hook("frozen_guard.py", {"hook_event_name":"PreToolUse","tool_name":tool,"session_id":"s","cwd":str(cwd),"tool_input":{"file_path":str(path)}})[0]
def prompt(text, cwd=repo): return hook("frozen_guard.py", {"hook_event_name":"UserPromptSubmit","session_id":"s","cwd":str(cwd),"prompt":text})[1]
def push(c): return hook("git_guard.py", {"hook_event_name":"PreToolUse","tool_name":"Bash","cwd":str(repo),"tool_input":{"command":c}})[0]
print("-- frozen_guard v2")
check("edit frozen", edit(repo/"payments.py"), True)
check("edit normal", edit(repo/"ui.py"), False)
check("marker mention in doc", edit(repo/"notes.md"), False)
check("symlink", edit(repo/"link.py"), True)
check("hardlink outside repo", edit(TMP/"hard.py"), True)
check("root file from subdir cwd", edit(repo/"payments.py", cwd=repo/"sub"), True)
check("relative path from subdir cwd", edit("../payments.py", cwd=repo/"sub"), True)
check("old/payments.py (not frozen)", edit(repo/"old"/"payments.py"), False)
check("Write tool on frozen", edit(repo/"payments.py", tool="Write"), True)
check("new file Write", edit(repo/"brand_new.py", tool="Write"), False)
check("frozen file inside worktree, builder cwd", edit(wt/"payments.py", cwd=wt), True)
(repo/"fresh_core.py").write_text("# FROZEN CORE: uncommitted\n")
check("untracked frozen file", edit(repo/"fresh_core.py"), True)
print("   bare override ->", prompt("frozen override").strip()[:70])
check("after bare override still denied", edit(repo/"payments.py"), True)
prompt("frozen override payments.py")
check("override: named path allowed", edit(repo/"payments.py"), False)
check("override: other core still denied", edit(repo/"sub"/"risk.py"), True)
check("override reaches worktree builder (Qwen's claim: allowed)", edit(wt/"payments.py", cwd=wt), False)
prompt("frozen override clear")
check("after clear denied again", edit(repo/"payments.py"), True)
p = subprocess.run(["python3", str(HERE/"frozen_guard.py")], input="garbage", capture_output=True, text=True, env=env)
check("garbage fail-open", p.returncode!=0 or bool(p.stdout), False)
check("non-repo cwd fail-open", edit(TMP/"x.py", cwd=TMP), False)
print("-- git_guard v2")
for name, c, want in [
 ("plain push", "git push origin main", False),
 ("push -f", "git push -f origin main", True),
 ("fetch && push --force", "git fetch origin && git push --force origin main", True),
 ("status && push +main", "git status && git push origin +main", True),
 ("+HEAD:main", "git push origin +HEAD:main", True),
 ("--force-with-lease", "git push --force-with-lease origin main", False),
 ("git -C x push -f", "git -C /tmp/x push -f", True),
 ("quoted && in commit msg then push", "git commit -m 'a && b' && git push origin main", False),
 ("no-space ;", "git fetch;git push -f origin main", True),
 ("no-space &&", "git fetch&&git push -f origin main", True),
 ("multi-line command", "git fetch origin\ngit push --force origin main", True),
 ("two gits one segment via newline, clean", "git fetch origin\ngit push origin main", False),
 ("combined flags -fu", "git push -fu origin main", True),
 ("subshell", "(cd /tmp && git push -f origin main)", True),
 ("commit msg mentioning force", "git commit -m 'never push --force' ", False),
 ("echo of a +1 then push", "git push origin main +1", True),
]:
    check(name, push(c), want)
print(f"\n{n-len(fails)}/{n}; failing: {fails}")
