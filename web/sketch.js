const API_BASE = "http://localhost:8000";

let treeData = null;
let segments = [];
let particles = [];
let runInterval = null;
let lastResult = null;

async function fetchState() {
  const response = await fetch(`${API_BASE}/state`);
  const data = await response.json();
  treeData = data.tree;
  updateStatus();
}

async function resetTree() {
  const response = await fetch(`${API_BASE}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  const data = await response.json();
  treeData = data.tree;
  lastResult = null;
  updateStatus();
}

async function stepSimulation() {
  const response = await fetch(`${API_BASE}/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ temperature_c: 25.0 }),
  });
  const data = await response.json();
  treeData = data.tree;
  lastResult = data.result;
  updateStatus();
}

async function pruneMetamer(targetId) {
  const response = await fetch(`${API_BASE}/prune`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ metamer_id: targetId }),
  });
  if (!response.ok) {
    console.warn("Prune failed", response.status);
    return;
  }
  const data = await response.json();
  treeData = data.tree;
  updateStatus();
}

function updateStatus() {
  const status = document.getElementById("status-text");
  if (!treeData) {
    status.textContent = "Loading...";
    return;
  }
  const activeCount = treeData.metamers.filter((metamer) => !metamer.is_pruned).length;
  const prunedCount = treeData.metamers.length - activeCount;
  const assimilation = lastResult ? lastResult.total_assimilation.toFixed(2) : "-";
  status.innerHTML = `
    <div>メタマー数: <strong>${treeData.metamers.length}</strong></div>
    <div>剪定済み: <strong>${prunedCount}</strong></div>
    <div>同化量: <strong>${assimilation}</strong></div>
  `;
}

function setup() {
  const canvas = createCanvas(900, 600);
  canvas.parent("canvas-container");
  strokeCap(ROUND);

  document.getElementById("step").addEventListener("click", () => {
    stepSimulation();
  });

  const runButton = document.getElementById("run");
  runButton.addEventListener("mousedown", () => {
    if (runInterval) {
      return;
    }
    runInterval = setInterval(stepSimulation, 350);
  });
  const stopRun = () => {
    if (runInterval) {
      clearInterval(runInterval);
      runInterval = null;
    }
  };
  runButton.addEventListener("mouseup", stopRun);
  runButton.addEventListener("mouseleave", stopRun);
  runButton.addEventListener("touchend", stopRun);

  document.getElementById("reset").addEventListener("click", () => {
    resetTree();
  });

  fetchState();
}

function draw() {
  background(15, 23, 42);
  drawTree();
  updateParticles();
}

function drawTree() {
  if (!treeData) {
    return;
  }
  segments = [];
  const childCounts = new Map();
  const centerX = width / 2;
  const baseY = height - 40;
  const positions = new Map();

  treeData.metamers.forEach((metamer) => {
    if (metamer.parent_id !== null) {
      childCounts.set(metamer.parent_id, (childCounts.get(metamer.parent_id) || 0) + 1);
    }
  });

  const sorted = [...treeData.metamers].sort((a, b) => a.order - b.order);
  sorted.forEach((metamer) => {
    if (metamer.is_pruned) {
      return;
    }
    let start;
    if (metamer.parent_id === null) {
      start = { x: centerX, y: baseY };
    } else {
      start = positions.get(metamer.parent_id);
    }
    if (!start) {
      start = { x: centerX, y: baseY };
    }
    const angleVector = metamer.angle_world || [0, 1, 0];
    const angle = Math.atan2(angleVector[1], angleVector[0]);
    const length = metamer.length * 500;
    const end = {
      x: start.x + Math.cos(angle) * length,
      y: start.y - Math.sin(angle) * length,
    };

    positions.set(metamer.id, end);
    const childCount = childCounts.get(metamer.id) || 0;
    segments.push({
      id: metamer.id,
      x1: start.x,
      y1: start.y,
      x2: end.x,
      y2: end.y,
      metamer,
      childCount,
    });
  });

  segments.forEach((segment) => {
    const { metamer } = segment;
    if (metamer.is_pruned) {
      return;
    }
    const congestion = segment.childCount;
    const efficiency = 1 / (1 + congestion * 0.7);
    const flowColor = lerpColor(color(16, 185, 129), color(248, 113, 113), 1 - efficiency);
    if (metamer.bud_status === "Active") {
      stroke(flowColor);
      strokeWeight(4);
    } else if (metamer.bud_status === "Dormant") {
      stroke(160, 98, 63);
      strokeWeight(2.5);
    } else {
      stroke(148, 163, 184);
      strokeWeight(3);
    }
    line(segment.x1, segment.y1, segment.x2, segment.y2);
    noStroke();
    fill(250, 204, 21);
    circle(segment.x2, segment.y2, metamer.bud_status === "Active" ? 8 : 5);
  });

  spawnParticles();
}

function mousePressed() {
  if (!segments.length) {
    return;
  }
  let closest = null;
  let minDist = Infinity;
  segments.forEach((segment) => {
    const dist = distanceToSegment(mouseX, mouseY, segment);
    if (dist < minDist) {
      minDist = dist;
      closest = segment;
    }
  });
  if (closest && minDist < 15) {
    pruneMetamer(closest.id);
  }
}

function distanceToSegment(px, py, segment) {
  const { x1, y1, x2, y2 } = segment;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) {
    return dist(px, py, x1, y1);
  }
  let t = ((px - x1) * dx + (py - y1) * dy) / lengthSquared;
  t = Math.max(0, Math.min(1, t));
  const projX = x1 + t * dx;
  const projY = y1 + t * dy;
  return dist(px, py, projX, projY);
}

function spawnParticles() {
  segments.forEach((segment) => {
    if (segment.metamer.is_pruned) {
      return;
    }
    if (Math.random() < 0.05) {
      particles.push({
        segment,
        t: 0,
        speed: 0.01 + Math.random() * 0.02,
      });
    }
  });
}

function updateParticles() {
  particles = particles.filter((particle) => particle.t <= 1);
  particles.forEach((particle) => {
    particle.t += particle.speed;
    const { segment } = particle;
    const x = lerp(segment.x1, segment.x2, particle.t);
    const y = lerp(segment.y1, segment.y2, particle.t);
    noStroke();
    fill(56, 189, 248, 200);
    circle(x, y, 4);
  });
}
