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
  const activeCount = treeData.metamers.filter((metamer) => !metamer.is_pruned).length;
  const prunedCount = treeData.metamers.length - activeCount;
  const assimilation = lastResult ? lastResult.total_assimilation.toFixed(2) : "-";
  status.innerHTML = `
    <div>メタマー数: <strong>${treeData.metamers.length}</strong></div>
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

function buildHierarchy() {
  if (!treeData) {
    return { roots: [], byId: new Map() };
  }
  const byId = new Map();
  treeData.metamers.forEach((metamer) => {
    byId.set(metamer.id, { ...metamer, children: [] });
  });
  treeData.metamers.forEach((metamer) => {
    if (metamer.parent_id !== null) {
      const parent = byId.get(metamer.parent_id);
      if (parent) {
        parent.children.push(byId.get(metamer.id));
      }
    }
  });
  const roots = treeData.roots && treeData.roots.length
    ? treeData.roots.map((rootId) => byId.get(rootId)).filter(Boolean)
    : treeData.metamers.filter((metamer) => metamer.parent_id === null).map((metamer) => byId.get(metamer.id));
  return { roots, byId };
}

function computePipeRadii(node) {
  const childRadii = node.children.map((child) => computePipeRadii(child));
  const childSum = childRadii.reduce((sum, radius) => sum + radius ** 2, 0);
  const baseRadius = Math.max(node.thickness * 0.5 * scaleConfig.thickness, 0.02);
  const radiusBottom = childSum > 0 ? Math.max(baseRadius, Math.sqrt(childSum)) : baseRadius;
  node.radiusBottom = radiusBottom;
  node.radiusTop = Math.max(radiusBottom * 0.6, 0.01);
  return radiusBottom;
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

  const { roots } = buildHierarchy();
  roots.forEach((root) => computePipeRadii(root));

  const goldenAngle = THREE.MathUtils.degToRad(137.5);
  const branchAngleBase = treeData.genotype_params?.branching_angle ?? 0.78;
  const branchAngleDeg = Math.min(70, Math.max(45, 45 + branchAngleBase * 30));
  const branchAngle = THREE.MathUtils.degToRad(branchAngleDeg);
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
    color: node.bud_status === "Active" ? 0x84cc16 : 0x94a3b8,
    emissive: node.bud_status === "Active" ? 0x7cfc00 : 0x000000,
    emissiveIntensity: node.bud_status === "Active" ? 1.2 : 0.0,
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
  const totalCarbon = tree.metamers.reduce((sum, metamer) => sum + (metamer.biomass_carbon || 0), 0);
  const totalNitrogen = (tree.root_system?.nitrogen_uptake || 1) * 4;
  const cnRatio = totalNitrogen > 0 ? totalCarbon / totalNitrogen : 0;
  const cnPercent = Math.min(100, Math.max(0, (cnRatio / 3) * 100));
  const shootMass = totalCarbon;
  const rootMass = tree.root_system?.nitrogen_uptake || 1;
  const trBalance = rootMass > 0 ? (shootMass / rootMass) : 0;
  const balanceAngle = Math.max(-30, Math.min(30, (trBalance - 1.0) * 12));

  return React.createElement(
    "div",
    { className: "status-grid" },
    React.createElement("div", { className: "status-label" }, "T/Rバランス"),
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
    React.createElement("div", { className: "status-label" }, "C/N比"),
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
      result ? "成長バイタル" : "成長バイタル (未計測)",
    ),
    React.createElement(
      "div",
      null,
      result ? `光合成余剰: ${result.total_assimilation.toFixed(2)}` : "シミュレーションを実行してください。",
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
