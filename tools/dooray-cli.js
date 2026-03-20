#!/usr/bin/env node
import fetch from "node-fetch";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CONFIG_FILE = path.join(__dirname, "dooray-config.json");
const BASE_URL = "https://api.dooray.com";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
function loadConfig() {
  let file = {};
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      file = JSON.parse(fs.readFileSync(CONFIG_FILE, "utf-8"));
    }
  } catch (e) {
    // ignore
  }
  return {
    token: file.token || process.env.DOORAY_TOKEN,
    projectId: file.projectId || process.env.DOORAY_PROJECT_ID,
    userName: file.userName,
    projects: file.projects || {},
  };
}

const config = loadConfig();

if (!config.token) {
  console.error("❌ Error: Dooray token not found. Set dooray-config.json or DOORAY_TOKEN env var.");
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Core helpers
// ---------------------------------------------------------------------------
async function doorayFetch(urlPath, { method = "GET", body } = {}) {
  const url = `${BASE_URL}${urlPath}`;
  const opts = {
    method,
    headers: {
      Authorization: `dooray-api ${config.token}`,
      "Content-Type": "application/json",
    },
  };
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON response (${res.status}): ${text.slice(0, 200)}`);
  }
  if (!res.ok) {
    const msg = data?.header?.resultMessage || data?.message || JSON.stringify(data);
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return data;
}

async function resolvePostId(postNumber, projectId) {
  const data = await doorayFetch(
    `/project/v1/projects/${projectId}/posts?postNumber=${postNumber}`
  );
  const results = data.result || data.results;
  if (!results || results.length === 0) {
    throw new Error(`Post #${postNumber} not found`);
  }
  const post = results[0];
  const postId = post.id;
  return { postId, post };
}

async function resolveWorkflowId(workflowName, projectId) {
  const data = await doorayFetch(`/project/v1/projects/${projectId}/workflows`);
  const workflows = data.result || data.results || [];
  // exact name
  let wf = workflows.find((w) => w.name === workflowName);
  if (wf) return wf;
  // exact class
  wf = workflows.find((w) => w.class === workflowName);
  if (wf) return wf;
  // partial match
  wf = workflows.find(
    (w) =>
      w.name?.includes(workflowName) || w.class?.includes(workflowName)
  );
  if (wf) return wf;
  throw new Error(
    `Workflow "${workflowName}" not found. Available: ${workflows.map((w) => w.name).join(", ")}`
  );
}

async function resolveMemberId(nameOrEmail) {
  const data = await doorayFetch(
    `/common/v1/members?name=${encodeURIComponent(nameOrEmail)}`
  );
  const members = data.result || data.results || [];
  if (members.length === 0) {
    throw new Error(`Member "${nameOrEmail}" not found`);
  }
  return members[0];
}

// ---------------------------------------------------------------------------
// Arg parser
// ---------------------------------------------------------------------------
function parseArgs(argv) {
  const args = argv.slice(3);
  const result = {};
  let i = 0;
  while (i < args.length) {
    const arg = args[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const next = args[i + 1];
      if (next === undefined || next.startsWith("--")) {
        result[key] = true;
        i++;
      } else {
        result[key] = next;
        i += 2;
      }
    } else {
      i++;
    }
  }
  return result;
}

function resolveProjectId(nameOrId) {
  if (!nameOrId) return null;
  // 숫자면 그대로 ID
  if (/^\d+$/.test(nameOrId)) return nameOrId;
  // 이름으로 매칭 (정확 매치 → 부분 매치)
  const projects = config.projects || {};
  if (projects[nameOrId]) return projects[nameOrId];
  const lower = nameOrId.toLowerCase();
  const match = Object.entries(projects).find(([k]) => k.toLowerCase().includes(lower));
  if (match) return match[1];
  throw new Error(`프로젝트 "${nameOrId}"를 찾을 수 없습니다. 사용 가능: ${Object.keys(projects).join(", ")}`);
}

function getProjectId(args) {
  const raw = args["project-id"] || args.project;
  if (raw) return resolveProjectId(raw);
  return config.projectId;
}

function requireProjectId(args) {
  const pid = getProjectId(args);
  if (!pid) throw new Error("--project-id required (or set projectId in dooray-config.json)");
  return pid;
}

function formatDate(dateStr) {
  // accept YYYY-MM-DD → YYYY-MM-DDT00:00:00+09:00
  if (!dateStr) return undefined;
  if (dateStr.includes("T")) return dateStr;
  return `${dateStr}T00:00:00+09:00`;
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

// A. Post Write

async function cmdCreatePost(args) {
  const pid = requireProjectId(args);
  if (!args.subject) throw new Error("--subject required");

  const body = {
    subject: args.subject,
    priority: args.priority || "normal",
  };

  if (args.body) {
    body.body = { content: args.body, mimeType: "text/x-markdown" };
  }

  if (args.parent) {
    const { postId } = await resolvePostId(args.parent, pid);
    body.parentPostId = postId;
  }

  const users = {};
  if (args.assignee) {
    const names = args.assignee.split(",").map((s) => s.trim());
    const members = await Promise.all(names.map((n) => resolveMemberId(n)));
    users.to = members.map((m) => ({
      type: "member",
      member: { organizationMemberId: m.id || m.organizationMemberId },
    }));
  }
  if (args.cc) {
    const names = args.cc.split(",").map((s) => s.trim());
    const members = await Promise.all(names.map((n) => resolveMemberId(n)));
    users.cc = members.map((m) => ({
      type: "member",
      member: { organizationMemberId: m.id || m.organizationMemberId },
    }));
  }
  if (Object.keys(users).length > 0) {
    body.users = users;
  }

  const data = await doorayFetch(`/project/v1/projects/${pid}/posts`, {
    method: "POST",
    body,
  });
  const post = data.result || data;
  const num = post.number || post.postNumber || "?";
  console.log(`✅ #${num} "${args.subject}" 생성 완료`);
}

async function cmdUpdatePost(args) {
  const pid = requireProjectId(args);
  if (!args.post) throw new Error("--post required");

  const { postId } = await resolvePostId(args.post, pid);
  const body = {};
  const changed = [];

  if (args.subject !== undefined) { body.subject = args.subject; changed.push("subject"); }
  if (args.body !== undefined) {
    body.body = { content: args.body, mimeType: "text/x-markdown" };
    changed.push("body");
  }
  if (args.priority !== undefined) { body.priority = args.priority; changed.push("priority"); }

  if (Object.keys(body).length === 0) throw new Error("Nothing to update. Provide --subject, --body, or --priority");

  await doorayFetch(`/project/v1/projects/${pid}/posts/${postId}`, {
    method: "PUT",
    body,
  });
  console.log(`✅ #${args.post} 수정 완료 (${changed.join(", ")})`);
}

async function cmdSetWorkflow(args) {
  const pid = requireProjectId(args);
  if (!args.post) throw new Error("--post required");
  if (!args.workflow) throw new Error("--workflow required");

  const { postId, post } = await resolvePostId(args.post, pid);
  const prevStatus = post.workflow?.name || post.workflowClass || "?";

  const wf = await resolveWorkflowId(args.workflow, pid);

  const toUsers = (post.users?.to || []).map((u) => ({
    type: u.type,
    member: u.member,
    workflow: { id: wf.id },
  }));

  await doorayFetch(`/project/v1/projects/${pid}/posts/${postId}`, {
    method: "PUT",
    body: { users: { to: toUsers } },
  });
  console.log(`✅ #${args.post} ${prevStatus} → ${wf.name}`);
}

async function cmdSetDone(args) {
  const pid = requireProjectId(args);
  if (!args.post) throw new Error("--post required");

  const { postId, post } = await resolvePostId(args.post, pid);
  const doneWf = await resolveWorkflowId("closed", pid);

  const toUsers = (post.users?.to || []).map((u) => ({
    type: u.type,
    member: u.member,
    workflow: { id: doneWf.id },
  }));

  await doorayFetch(`/project/v1/projects/${pid}/posts/${postId}`, {
    method: "PUT",
    body: { users: { to: toUsers } },
  });
  console.log(`✅ #${args.post} 완료 처리`);
}

async function cmdAddComment(args) {
  const pid = requireProjectId(args);
  if (!args.post) throw new Error("--post required");
  if (!args.content) throw new Error("--content required");

  const { postId } = await resolvePostId(args.post, pid);
  await doorayFetch(`/project/v1/projects/${pid}/posts/${postId}/logs`, {
    method: "POST",
    body: { body: { content: args.content, mimeType: "text/x-markdown" } },
  });
  console.log(`✅ #${args.post}에 댓글 추가 완료`);
}

async function cmdUpdateComment(args) {
  const pid = requireProjectId(args);
  if (!args.post) throw new Error("--post required");
  if (!args["log-id"]) throw new Error("--log-id required");
  if (!args.content) throw new Error("--content required");

  const { postId } = await resolvePostId(args.post, pid);
  await doorayFetch(
    `/project/v1/projects/${pid}/posts/${postId}/logs/${args["log-id"]}`,
    {
      method: "PUT",
      body: { body: { content: args.content, mimeType: "text/x-markdown" } },
    }
  );
  console.log(`✅ #${args.post} 댓글 ${args["log-id"]} 수정 완료`);
}

async function cmdDeleteComment(args) {
  const pid = requireProjectId(args);
  if (!args.post) throw new Error("--post required");
  if (!args["log-id"]) throw new Error("--log-id required");

  const { postId } = await resolvePostId(args.post, pid);
  await doorayFetch(
    `/project/v1/projects/${pid}/posts/${postId}/logs/${args["log-id"]}`,
    { method: "DELETE" }
  );
  console.log(`✅ #${args.post} 댓글 ${args["log-id"]} 삭제 완료`);
}

// B. Messenger

async function cmdSendMessage(args) {
  if (!args["channel-id"]) throw new Error("--channel-id required");
  if (!args.content) throw new Error("--content required");

  await doorayFetch(`/messenger/v1/channels/${args["channel-id"]}/send`, {
    method: "POST",
    body: { text: args.content },
  });
  console.log(`✅ 채널 ${args["channel-id"]}에 메시지 전송 완료`);
}

async function cmdCreateChannel(args) {
  if (!args.name) throw new Error("--name required");

  const body = {
    title: args.name,
    capacity: 100,
    channelType: "private",
  };

  if (args.members) {
    const names = args.members.split(",").map((s) => s.trim());
    const members = await Promise.all(names.map((n) => resolveMemberId(n)));
    body.members = members.map((m) => ({
      type: "memberId",
      member: { organizationMemberId: m.id || m.organizationMemberId },
    }));
  }

  const data = await doorayFetch("/messenger/v1/channels", {
    method: "POST",
    body,
  });
  const ch = data.result || data;
  const channelId = ch.id || ch.channelId || "?";
  console.log(`✅ 채널 "${args.name}" 생성 완료 (id: ${channelId})`);
}

async function cmdChannelMembers(args) {
  if (!args["channel-id"]) throw new Error("--channel-id required");
  if (!args.action) throw new Error("--action required (join/leave)");
  if (!args.members) throw new Error("--members required");

  const names = args.members.split(",").map((s) => s.trim());
  const members = await Promise.all(names.map((n) => resolveMemberId(n)));
  const memberList = members.map((m) => ({
    type: "memberId",
    member: { organizationMemberId: m.id || m.organizationMemberId },
  }));

  await doorayFetch(
    `/messenger/v1/channels/${args["channel-id"]}/members/${args.action}`,
    { method: "POST", body: { members: memberList } }
  );
  console.log(`✅ 채널 ${args["channel-id"]} ${args.action} 완료 (${names.join(", ")})`);
}

// C. Milestone CRUD

async function cmdCreateMilestone(args) {
  const pid = requireProjectId(args);
  if (!args.name) throw new Error("--name required");

  const body = { name: args.name };
  if (args.start) body.startAt = formatDate(args.start);
  if (args.end) body.endAt = formatDate(args.end);

  const data = await doorayFetch(`/project/v1/projects/${pid}/milestones`, {
    method: "POST",
    body,
  });
  const ms = data.result || data;
  const msId = ms.id || "?";
  console.log(`✅ 마일스톤 "${args.name}" 생성 완료 (id: ${msId})`);
}

async function cmdUpdateMilestone(args) {
  const pid = requireProjectId(args);
  if (!args.id) throw new Error("--id required");

  const body = {};
  const changed = [];
  if (args.name !== undefined) { body.name = args.name; changed.push("name"); }
  if (args.start !== undefined) { body.startAt = formatDate(args.start); changed.push("startAt"); }
  if (args.end !== undefined) { body.endAt = formatDate(args.end); changed.push("endAt"); }
  if (args.status !== undefined) { body.status = args.status; changed.push("status"); }

  if (Object.keys(body).length === 0) throw new Error("Nothing to update.");

  await doorayFetch(`/project/v1/projects/${pid}/milestones/${args.id}`, {
    method: "PUT",
    body,
  });
  console.log(`✅ 마일스톤 ${args.id} 수정 완료 (${changed.join(", ")})`);
}

async function cmdDeleteMilestone(args) {
  const pid = requireProjectId(args);
  if (!args.id) throw new Error("--id required");

  await doorayFetch(`/project/v1/projects/${pid}/milestones/${args.id}`, {
    method: "DELETE",
  });
  console.log(`✅ 마일스톤 ${args.id} 삭제 완료`);
}

// D. Wiki Write

async function cmdWikiCreatePage(args) {
  if (!args["wiki-id"]) throw new Error("--wiki-id required");
  if (!args.title) throw new Error("--title required");
  if (!args.body) throw new Error("--body required");

  const body = {
    subject: args.title,
    body: { content: args.body, mimeType: "text/x-markdown" },
  };
  if (args["parent-page-id"]) body.parentPageId = args["parent-page-id"];

  const data = await doorayFetch(`/wiki/v1/wikis/${args["wiki-id"]}/pages`, {
    method: "POST",
    body,
  });
  const page = data.result || data;
  const pageId = page.id || "?";
  console.log(`✅ 위키 페이지 "${args.title}" 생성 완료 (id: ${pageId})`);
}

async function cmdWikiUpdatePage(args) {
  if (!args["wiki-id"]) throw new Error("--wiki-id required");
  if (!args["page-id"]) throw new Error("--page-id required");

  const body = {};
  const changed = [];
  if (args.title !== undefined) { body.subject = args.title; changed.push("title"); }
  if (args.body !== undefined) {
    body.body = { content: args.body, mimeType: "text/x-markdown" };
    changed.push("body");
  }
  if (Object.keys(body).length === 0) throw new Error("Nothing to update. Provide --title or --body");

  await doorayFetch(
    `/wiki/v1/wikis/${args["wiki-id"]}/pages/${args["page-id"]}`,
    { method: "PUT", body }
  );
  console.log(`✅ 위키 페이지 ${args["page-id"]} 수정 완료 (${changed.join(", ")})`);
}

async function cmdWikiAddComment(args) {
  if (!args["wiki-id"]) throw new Error("--wiki-id required");
  if (!args["page-id"]) throw new Error("--page-id required");
  if (!args.content) throw new Error("--content required");

  await doorayFetch(
    `/wiki/v1/wikis/${args["wiki-id"]}/pages/${args["page-id"]}/comments`,
    {
      method: "POST",
      body: { body: { content: args.content, mimeType: "text/x-markdown" } },
    }
  );
  console.log(`✅ 위키 페이지 ${args["page-id"]}에 댓글 추가 완료`);
}

// E. Open in browser

async function cmdOpen(args) {
  if (!args.post) throw new Error("--post required");
  const pid = requireProjectId(args);
  const { postId } = await resolvePostId(args.post, pid);
  const url = `https://nhn.dooray.com/task/${pid}/${postId}`;
  const { exec } = await import("child_process");
  exec(`open "${url}"`);
  console.log(`🔗 ${url}`);
}

// F. Read / Query

async function cmdGetPost(args) {
  const pid = requireProjectId(args);
  if (!args.post) throw new Error("--post required");
  const data = await doorayFetch(
    `/project/v1/projects/${pid}/posts?postNumber=${args.post}`
  );
  const results = data.result || [];
  if (results.length === 0) throw new Error(`Post #${args.post} not found`);
  const post = results[0];
  console.log(JSON.stringify(post, null, 2));
}

async function cmdGetPostDetail(args) {
  const pid = requireProjectId(args);
  if (!args.post) throw new Error("--post required");
  const { postId } = await resolvePostId(args.post, pid);
  const data = await doorayFetch(`/project/v1/projects/${pid}/posts/${postId}`);
  const result = data.result || {};
  console.log(JSON.stringify(result, null, 2));
}

async function cmdGetPostLogs(args) {
  const pid = requireProjectId(args);
  if (!args.post) throw new Error("--post required");
  const { postId } = await resolvePostId(args.post, pid);
  const data = await doorayFetch(`/project/v1/projects/${pid}/posts/${postId}/logs`);
  const logs = data.result || [];
  console.log(JSON.stringify(logs, null, 2));
}

async function cmdListChildPosts(args) {
  const pid = requireProjectId(args);
  if (!args.parent) throw new Error("--parent required (상위업무 번호)");
  const { postId } = await resolvePostId(args.parent, pid);
  const size = args.size || "100";
  const data = await doorayFetch(
    `/project/v1/projects/${pid}/posts?parentPostId=${postId}&size=${size}`
  );
  let posts = data.result || [];
  if (args["exclude-done"]) {
    posts = posts.filter((p) => !p.closed);
  }
  console.log(JSON.stringify(posts, null, 2));
}

async function cmdSearchPosts(args) {
  const pid = requireProjectId(args);
  const query = new URLSearchParams();
  query.set("page", args.page || "0");
  query.set("size", args.size || "20");
  if (args["workflow-class"]) query.set("workflowClass", args["workflow-class"]);
  if (args["milestone-id"]) query.set("milestoneIds", args["milestone-id"]);
  if (args["tag-ids"]) query.set("tagIds", args["tag-ids"]);
  if (args["created-from"]) {
    const val = args["created-from"] + (args["created-to"] ? `~${args["created-to"]}` : "");
    query.set("createdAt", val);
  }
  if (args["due-from"]) {
    const val = args["due-from"] + (args["due-to"] ? `~${args["due-to"]}` : "");
    query.set("dueAt", val);
  }
  if (args.assignee) {
    const member = await resolveMemberId(args.assignee);
    query.set("toMemberIds", member.id || member.organizationMemberId);
  }
  if (args.parent) {
    const { postId } = await resolvePostId(args.parent, pid);
    query.set("parentPostId", postId);
  }
  const data = await doorayFetch(`/project/v1/projects/${pid}/posts?${query.toString()}`);
  const posts = data.result || [];
  console.log(JSON.stringify({ totalCount: data.totalCount || posts.length, result: posts }, null, 2));
}

async function cmdMyTasks(args) {
  const pid = requireProjectId(args);
  const userName = config.userName || "";
  if (!userName) throw new Error("dooray-config.json에 userName이 설정되지 않았습니다.");
  const member = await resolveMemberId(userName);
  const query = new URLSearchParams({
    page: "0",
    size: args.size || "30",
    toMemberIds: member.id || member.organizationMemberId,
  });
  const wfClass = args["workflow-class"] || "working";
  query.set("workflowClass", wfClass);
  const data = await doorayFetch(`/project/v1/projects/${pid}/posts?${query.toString()}`);
  const posts = data.result || [];
  console.log(JSON.stringify({ totalCount: data.totalCount || posts.length, result: posts }, null, 2));
}

async function cmdListWorkflows(args) {
  const pid = requireProjectId(args);
  const data = await doorayFetch(`/project/v1/projects/${pid}/workflows`);
  const workflows = data.result || data.results || [];
  console.log(JSON.stringify(workflows, null, 2));
}

async function cmdSearchMembers(args) {
  const query = new URLSearchParams();
  if (args.name) query.set("name", args.name);
  if (args.email) query.set("externalEmailAddresses", args.email);
  if (args["user-code"]) query.set("userCode", args["user-code"]);
  if ([...query].length === 0) throw new Error("--name, --email, --user-code 중 하나 이상 필요");
  const data = await doorayFetch(`/common/v1/members?${query.toString()}`);
  const members = data.result || [];
  console.log(JSON.stringify(members, null, 2));
}

async function cmdListMilestones(args) {
  const pid = requireProjectId(args);
  const query = new URLSearchParams({ page: "0", size: "100" });
  const status = args.status || "open";
  if (status !== "all") query.set("status", status);
  const data = await doorayFetch(`/project/v1/projects/${pid}/milestones?${query.toString()}`);
  const milestones = data.result || [];
  console.log(JSON.stringify(milestones, null, 2));
}

async function cmdListChannels(args) {
  const query = new URLSearchParams({
    page: args.page || "0",
    size: args.size || "20",
  });
  const data = await doorayFetch(`/messenger/v1/channels?${query.toString()}`);
  const channels = data.result || [];
  console.log(JSON.stringify(channels, null, 2));
}

// F. Wiki Read

async function cmdWikiList(args) {
  const query = new URLSearchParams({
    page: args.page || "0",
    size: args.size || "100",
  });
  const data = await doorayFetch(`/wiki/v1/wikis?${query.toString()}`);
  let wikis = data.result || [];
  if (args.name) {
    const lower = args.name.toLowerCase();
    wikis = wikis.filter((w) => w.name?.toLowerCase().includes(lower));
  }
  console.log(JSON.stringify(wikis, null, 2));
}

async function cmdWikiGetPage(args) {
  if (!args["page-id"]) throw new Error("--page-id required");
  // wiki-id가 있으면 wiki 경로, 없으면 직접 page 경로
  const url = args["wiki-id"]
    ? `/wiki/v1/wikis/${args["wiki-id"]}/pages/${args["page-id"]}`
    : `/wiki/v1/pages/${args["page-id"]}`;
  const data = await doorayFetch(url);
  console.log(JSON.stringify(data.result || data, null, 2));
}

async function cmdWikiListPages(args) {
  if (!args["wiki-id"]) throw new Error("--wiki-id required");
  let url = `/wiki/v1/wikis/${args["wiki-id"]}/pages`;
  if (args["parent-page-id"]) {
    url += `?parentPageId=${args["parent-page-id"]}`;
  }
  const data = await doorayFetch(url);
  console.log(JSON.stringify(data.result || [], null, 2));
}

async function cmdWikiListComments(args) {
  if (!args["wiki-id"]) throw new Error("--wiki-id required");
  if (!args["page-id"]) throw new Error("--page-id required");
  const query = new URLSearchParams({
    page: args.page || "0",
    size: args.size || "20",
  });
  const data = await doorayFetch(
    `/wiki/v1/wikis/${args["wiki-id"]}/pages/${args["page-id"]}/comments?${query.toString()}`
  );
  console.log(JSON.stringify(data.result || [], null, 2));
}

async function cmdWikiGetComment(args) {
  if (!args["wiki-id"]) throw new Error("--wiki-id required");
  if (!args["page-id"]) throw new Error("--page-id required");
  if (!args["comment-id"]) throw new Error("--comment-id required");
  const data = await doorayFetch(
    `/wiki/v1/wikis/${args["wiki-id"]}/pages/${args["page-id"]}/comments/${args["comment-id"]}`
  );
  console.log(JSON.stringify(data.result || data, null, 2));
}

async function cmdWikiListSharedLinks(args) {
  if (!args["wiki-id"]) throw new Error("--wiki-id required");
  if (!args["page-id"]) throw new Error("--page-id required");
  const query = new URLSearchParams({
    page: args.page || "0",
    size: args.size || "20",
    valid: args.valid || "true",
  });
  const data = await doorayFetch(
    `/wiki/v1/wikis/${args["wiki-id"]}/pages/${args["page-id"]}/shared-links?${query.toString()}`
  );
  console.log(JSON.stringify(data.result || [], null, 2));
}

// G. Tags

async function cmdCreateTag(args) {
  const pid = requireProjectId(args);
  if (!args.name) throw new Error("--name required");

  const data = await doorayFetch(`/project/v1/projects/${pid}/tags`, {
    method: "POST",
    body: { name: args.name, color: args.color || "blue" },
  });
  const tag = data.result || data;
  const tagId = tag.id || "?";
  console.log(`✅ 태그 "${args.name}" 생성 완료 (id: ${tagId})`);
}

async function cmdListTags(args) {
  const pid = requireProjectId(args);
  const data = await doorayFetch(`/project/v1/projects/${pid}/tags`);
  const tags = data.result || data.results || [];
  if (tags.length === 0) {
    console.log("(태그 없음)");
    return;
  }
  tags.forEach((t) => console.log(`  ${t.id}  ${t.name}  [${t.color || ""}]`));
}

// ---------------------------------------------------------------------------
// Help
// ---------------------------------------------------------------------------
function printHelp() {
  console.log(`
dooray-cli.js — Dooray API CLI (read + write)

Usage: node dooray-cli.js <command> [options]

OPEN
  open              --post NUM [--project-id ID]                           브라우저에서 이슈 열기

POST READ
  get-post          --post NUM [--project-id ID]                           업무 기본 조회
  get-post-detail   --post NUM [--project-id ID]                           업무 상세 조회 (본문 포함)
  get-post-logs     --post NUM [--project-id ID]                           댓글/로그 조회
  list-child-posts  --parent NUM [--exclude-done] [--size N] [--project-id ID]  하위 업무 목록
  search-posts      [--workflow-class registered|working|done] [--assignee NAME]
                    [--milestone-id ID] [--tag-ids IDS] [--parent NUM]
                    [--created-from DATE] [--created-to DATE]
                    [--due-from DATE] [--due-to DATE]
                    [--page N] [--size N] [--project-id ID]                업무 검색
  my-tasks          [--workflow-class registered|working|done] [--size N] [--project-id ID]  내 업무

METADATA READ
  list-workflows    [--project-id ID]                                      워크플로우 목록
  search-members    [--name STR] [--email STR] [--user-code STR]           멤버 검색
  list-milestones   [--status open|closed|all] [--project-id ID]           마일스톤 목록
  list-channels     [--page N] [--size N]                                  메신저 채널 목록

WIKI READ
  wiki-list           [--name STR] [--page N] [--size N]                   위키 목록 (이름 필터)
  wiki-get-page       --page-id ID [--wiki-id ID]                          위키 페이지 조회
  wiki-list-pages     --wiki-id ID [--parent-page-id ID]                   위키 페이지 목록
  wiki-list-comments  --wiki-id ID --page-id ID [--page N] [--size N]      위키 댓글 목록
  wiki-get-comment    --wiki-id ID --page-id ID --comment-id ID            위키 댓글 상세
  wiki-list-shared-links --wiki-id ID --page-id ID [--page N] [--size N]   공유 링크 목록

POST WRITE
  create-post     --subject STR [--body STR] [--parent NUM] [--assignee NAME,...] [--cc NAME,...] [--priority STR] [--project-id ID]
  update-post     --post NUM [--subject STR] [--body STR] [--priority STR] [--project-id ID]
  set-workflow    --post NUM --workflow NAME [--project-id ID]
  set-done        --post NUM [--project-id ID]
  add-comment     --post NUM --content STR [--project-id ID]
  update-comment  --post NUM --log-id ID --content STR [--project-id ID]
  delete-comment  --post NUM --log-id ID [--project-id ID]

MESSENGER
  send-message    --channel-id ID --content STR
  create-channel  --name STR [--members NAME,...]
  channel-members --channel-id ID --action join|leave --members NAME,...

MILESTONE
  create-milestone  --name STR [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--project-id ID]
  update-milestone  --id ID [--name STR] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--status open|closed] [--project-id ID]
  delete-milestone  --id ID [--project-id ID]

WIKI
  wiki-create-page  --wiki-id ID --title STR --body STR [--parent-page-id ID]
  wiki-update-page  --wiki-id ID --page-id ID [--title STR] [--body STR]
  wiki-add-comment  --wiki-id ID --page-id ID --content STR

TAGS
  create-tag  --name STR [--color STR] [--project-id ID]
  list-tags   [--project-id ID]
`);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
const COMMANDS = {
  // Open
  "open": cmdOpen,
  // Read
  "get-post": cmdGetPost,
  "get-post-detail": cmdGetPostDetail,
  "get-post-logs": cmdGetPostLogs,
  "list-child-posts": cmdListChildPosts,
  "search-posts": cmdSearchPosts,
  "my-tasks": cmdMyTasks,
  "list-workflows": cmdListWorkflows,
  "search-members": cmdSearchMembers,
  "list-milestones": cmdListMilestones,
  "list-channels": cmdListChannels,
  // Wiki Read
  "wiki-list": cmdWikiList,
  "wiki-get-page": cmdWikiGetPage,
  "wiki-list-pages": cmdWikiListPages,
  "wiki-list-comments": cmdWikiListComments,
  "wiki-get-comment": cmdWikiGetComment,
  "wiki-list-shared-links": cmdWikiListSharedLinks,
  // Write
  "create-post": cmdCreatePost,
  "update-post": cmdUpdatePost,
  "set-workflow": cmdSetWorkflow,
  "set-done": cmdSetDone,
  "add-comment": cmdAddComment,
  "update-comment": cmdUpdateComment,
  "delete-comment": cmdDeleteComment,
  "send-message": cmdSendMessage,
  "create-channel": cmdCreateChannel,
  "channel-members": cmdChannelMembers,
  "create-milestone": cmdCreateMilestone,
  "update-milestone": cmdUpdateMilestone,
  "delete-milestone": cmdDeleteMilestone,
  "wiki-create-page": cmdWikiCreatePage,
  "wiki-update-page": cmdWikiUpdatePage,
  "wiki-add-comment": cmdWikiAddComment,
  "create-tag": cmdCreateTag,
  "list-tags": cmdListTags,
};

async function main() {
  const command = process.argv[2];

  if (!command || command === "--help" || command === "-h") {
    printHelp();
    process.exit(0);
  }

  const fn = COMMANDS[command];
  if (!fn) {
    console.error(`❌ Error: Unknown command "${command}"`);
    printHelp();
    process.exit(1);
  }

  const args = parseArgs(process.argv);

  try {
    await fn(args);
    process.exit(0);
  } catch (err) {
    console.error(`❌ Error: ${err.message}`);
    process.exit(1);
  }
}

main();
