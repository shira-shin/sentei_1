const API_BASE = "http://localhost:8000";

let treeData = null;
let lastResult = null;
let scene = null;
let camera = null;
let renderer = null;
let controls = null;
let treeGroup = null;
let runInterval = null;
let panelRoot = null;

const scaleConfig = {
  length: 6.5,
  thickness: 0.22,
};

async function fetchState() {
  const response = await fetch(`${API_BASE}/state`);
  const data = await response.json();
  treeData = data.tree;
  updateStatus();
  rebuildTree();
  renderPanels();
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
  rebuildTree();
  renderPanels();
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
  rebuildTree();
  renderPanels();
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
  rebuildTree();
  renderPanels();
}

function updateStatus() {
  const status = document.getElementById("status-text");
  if (!treeData) {
    status.textContent = "Loading...";
    return;
  }
  const allMetamers = collectMetamers(treeData);
  const activeCount = allMetamers.filter((metamer) => !metamer.is_pruned).length;
  const prunedCount = allMetamers.length - activeCount;
  const assimilation = lastResult ? lastResult.total_assimilation.toFixed(2) : "-";
  status.innerHTML = `
    <div>メタマー数: <strong>${allMetamers.length}</strong></div>
    <div>剪定済み: <strong>${prunedCount}</strong></div>
    <div>同化量: <strong>${assimilation}</strong></div>
  `;
}

function initScene() {
  const container = document.getElementById("canvas-container");
  const width = container.clientWidth;
  const height = container.clientHeight;

  scene = new THREE.Scene();
  scene.background = new THREE.Color("#0d1117");

  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 200);
  camera.position.set(0, 8, 18);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  container.appendChild(renderer.domElement);

  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.minDistance = 6;
  controls.maxDistance = 40;

  const ambient = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambient);
  const directional = new THREE.DirectionalLight(0xffffff, 0.9);
  directional.position.set(8, 12, 6);
  scene.add(directional);

  const grid = new THREE.GridHelper(60, 30, 0x1f2937, 0x111827);
  grid.position.y = -0.01;
  scene.add(grid);
  const axes = new THREE.AxesHelper(6);
  axes.setColors(0x38bdf8, 0xf97316, 0x22c55e);
  scene.add(axes);

  treeGroup = new THREE.Group();
  scene.add(treeGroup);

  window.addEventListener("resize", () => {
    const newWidth = container.clientWidth;
    const newHeight = container.clientHeight;
    renderer.setSize(newWidth, newHeight);
    camera.aspect = newWidth / newHeight;
    camera.updateProjectionMatrix();
  });

  renderer.domElement.addEventListener("click", handleClick);
  animate();
}

function animate() {
  requestAnimationFrame(animate);
  if (controls) {
    controls.update();
  }
  if (renderer && scene && camera) {
    renderer.render(scene, camera);
  }
}

function collectMetamers(tree) {
  if (!tree || !tree.roots) {
    return [];
  }
  const result = [];
  const stack = [...tree.roots];
  while (stack.length) {
    const node = stack.pop();
    if (!node) {
      continue;
    }
    result.push(node);
    if (node.children && node.children.length) {
      stack.push(...node.children);
    }
  }
  return result;
}

function computePipeRadii(node) {
  const radiusScale = scaleConfig.thickness * 0.015;
  const minRadius = 0.015;
  if (node.is_pruned) {
    node.radiusBottom = minRadius;
    node.radiusTop = minRadius;
    node.descendantLeafArea = 0;
    return 0;
  }
  const childAreas = node.children.map((child) => computePipeRadii(child));
  const childSum = childAreas.reduce((sum, area) => sum + area, 0);
  const descendantLeafArea = (node.leaf_area || 0) + childSum;
  const radiusBottom = Math.max(minRadius, Math.sqrt(descendantLeafArea) * radiusScale);
  const radiusTop = childSum > 0
    ? Math.max(minRadius, Math.sqrt(childSum) * radiusScale)
    : Math.max(minRadius, radiusBottom * 0.45);
  node.radiusBottom = radiusBottom;
  node.radiusTop = radiusTop;
  node.descendantLeafArea = descendantLeafArea;
  return descendantLeafArea;
}

function rebuildTree() {
  if (!scene || !treeGroup) {
    return;
  }
  while (treeGroup.children.length) {
    treeGroup.remove(treeGroup.children[0]);
  }
  if (!treeData) {
    return;
  }
  const roots = treeData.roots || [];
  roots.forEach((root) => computePipeRadii(root));

  const goldenAngle = THREE.MathUtils.degToRad(137.5);
  const branchAngle = treeData.genotype_params?.branching_angle ?? THREE.MathUtils.degToRad(45);
  const baseDirection = new THREE.Vector3(0, 1, 0);
  const origin = new THREE.Vector3(0, 0, 0);

  roots.forEach((root) => {
    buildSegment(root, origin, baseDirection, 0, branchAngle, goldenAngle);
  });
}

function buildSegment(node, start, direction, depth, branchAngle, goldenAngle) {
  if (node.is_pruned) {
    return;
  }
  const length = node.length * scaleConfig.length;
  const radiusTop = node.radiusTop || 0.03;
  const radiusBottom = node.radiusBottom || 0.05;
  const geometry = new THREE.CylinderGeometry(radiusTop, radiusBottom, length, 8);
  const color = node.bud_status === "Active" ? 0x4ade80 : 0x8b5e3c;
  const material = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.6,
    metalness: 0.1,
  });
  const cylinder = new THREE.Mesh(geometry, material);
  const up = new THREE.Vector3(0, 1, 0);
  const quaternion = new THREE.Quaternion().setFromUnitVectors(up, direction.clone().normalize());
  cylinder.quaternion.copy(quaternion);
  const midPoint = start.clone().add(direction.clone().normalize().multiplyScalar(length / 2));
  cylinder.position.copy(midPoint);
  treeGroup.add(cylinder);

  const endPoint = start.clone().add(direction.clone().normalize().multiplyScalar(length));
  const budMaterial = new THREE.MeshStandardMaterial({
    color: node.bud_status === "Active" ? 0xcaff33 : 0x94a3b8,
    emissive: node.bud_status === "Active" ? 0x9aff00 : 0x000000,
    emissiveIntensity: node.bud_status === "Active" ? 3.5 : 0.0,
  });
  const bud = new THREE.Mesh(new THREE.SphereGeometry(radiusTop * 1.2, 12, 12), budMaterial);
  bud.position.copy(endPoint);
  bud.userData = { metamerId: node.id };
  treeGroup.add(bud);

  const axisFallback = Math.abs(direction.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
  const baseAxis = new THREE.Vector3().crossVectors(direction, axisFallback).normalize();

  node.children.forEach((child, index) => {
    const spiralAngle = goldenAngle * (index + depth + 1);
    const spiralQuat = new THREE.Quaternion().setFromAxisAngle(direction, spiralAngle);
    const branchQuat = new THREE.Quaternion().setFromAxisAngle(baseAxis, branchAngle);
    const newDirection = direction.clone().applyQuaternion(spiralQuat).applyQuaternion(branchQuat).normalize();
    buildSegment(child, endPoint, newDirection, depth + 1, branchAngle, goldenAngle);
  });
}

function handleClick(event) {
  if (!treeData || !camera || !renderer) {
    return;
  }
  const rect = renderer.domElement.getBoundingClientRect();
  const mouse = new THREE.Vector2(
    ((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1,
  );
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(treeGroup.children, true);
  const hit = intersects.find((item) => item.object.userData?.metamerId);
  if (hit) {
    pruneMetamer(hit.object.userData.metamerId);
  }
}

function renderPanels() {
  const root = document.getElementById("react-panels");
  if (!root || !treeData) {
    return;
  }
  if (!panelRoot) {
    panelRoot = ReactDOM.createRoot(root);
  }
  panelRoot.render(
    React.createElement(PanelDashboard, {
      tree: treeData,
      result: lastResult,
    }),
  );
}

function PanelDashboard({ tree, result }) {
  const allMetamers = collectMetamers(tree);
  const totalCarbon = allMetamers.reduce((sum, metamer) => sum + (metamer.biomass_carbon || 0), 0);
  const totalNitrogen = (tree.root_system?.nitrogen_uptake || 1) * 4;
  const cnRatio = totalNitrogen > 0 ? totalCarbon / totalNitrogen : 0;
  const cnPercent = Math.min(100, Math.max(0, (cnRatio / 3) * 100));
  const shootMass = totalCarbon;
  const rootMass = tree.root_system?.nitrogen_uptake || 1;
  const trBalance = rootMass > 0 ? (shootMass / rootMass) : 0;
  const balanceAngle = Math.max(-30, Math.min(30, (trBalance - 1.0) * 12));
  const assimilation = result?.total_assimilation ?? 0;
  const energyPercent = Math.max(0, Math.min(100, ((assimilation + 2) / 6) * 100));
  let statusMessage = "シミュレーションを実行してください。";
  if (result) {
    if (assimilation < 0.4) {
      statusMessage = "現在は貯蔵養分を消費して新鞘を伸ばしています。";
    } else if (assimilation < 1.6) {
      statusMessage = "光合成と呼吸が拮抗し、次の葉の準備を進めています。";
    } else {
      statusMessage = "同化が優勢で、新しい葉を展開するフェーズです。";
    }
  }

  return React.createElement(
    "div",
    { className: "status-grid" },
    React.createElement(
      "div",
      { className: "status-label" },
      React.createElement("span", { className: "label-icon" }, "⚖︎"),
      "T/Rバランス",
    ),
    React.createElement(
      "div",
      { className: "meter-track" },
      React.createElement("div", { className: "scale-bar" }),
      React.createElement("div", {
        className: "scale-arm",
        style: { transform: `translateX(-50%) rotate(${balanceAngle}deg)` },
      }),
      React.createElement("div", { className: "scale-pillar" }),
      React.createElement("div", { className: "scale-labels" }, [
        React.createElement("span", { key: "root" }, "Root"),
        React.createElement("span", { key: "shoot" }, "Shoot"),
      ]),
    ),
    React.createElement(
      "div",
      { className: "status-label" },
      React.createElement("span", { className: "label-icon" }, "◔"),
      "C/N比",
    ),
    React.createElement(
      "div",
      { style: { position: "relative" } },
      React.createElement("div", {
        className: "donut",
        style: { "--fill": `${cnPercent * 3.6}deg` },
      }),
      React.createElement("div", { className: "donut-value" }, `${cnRatio.toFixed(2)}`),
    ),
    React.createElement(
      "div",
      { className: "status-label" },
      React.createElement("span", { className: "label-icon" }, "⚡"),
      "現在のエネルギー状態",
    ),
    React.createElement(
      "div",
      { className: "energy-track" },
      React.createElement("div", {
        className: "energy-fill",
        style: { width: `${energyPercent}%` },
      }),
      React.createElement(
        "div",
        { className: "energy-value" },
        result ? `${assimilation.toFixed(2)} units` : "--",
      ),
    ),
    React.createElement(
      "div",
      { className: "status-label" },
      React.createElement("span", { className: "label-icon" }, "🧪"),
      "ステータス診断",
    ),
    React.createElement(
      "div",
      { className: "status-message" },
      statusMessage,
    ),
  );
}

function setupControls() {
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
}

setupControls();
initScene();
fetchState();
