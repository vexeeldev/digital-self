'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export default function DesainPage() {
  const mountRef = useRef<HTMLDivElement>(null);

  // Customizer Controls State
  const [wireColor, setWireColor] = useState<string>('#06b6d4');
  const [wireOpacity, setWireOpacity] = useState<number>(0.2);
  const [autoRotate, setAutoRotate] = useState<boolean>(true);
  const [rotateSpeed, setRotateSpeed] = useState<number>(1.5);
  const [showBrainCore, setShowBrainCore] = useState<boolean>(true);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const skullGroupRef = useRef<THREE.Group | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const materialsRef = useRef<THREE.MeshBasicMaterial[]>([]);

  useEffect(() => {
    if (!mountRef.current) return;

    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    // 1. Scene Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#030712');
    sceneRef.current = scene;

    // 2. Camera Setup
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 2000);
    camera.position.set(0, 30, 600);

    // 3. Renderer Setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mountRef.current.appendChild(renderer.domElement);

    // 4. Orbit Controls (360° Rotate, Pan, Zoom)
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = rotateSpeed;
    controls.maxDistance = 1200;
    controls.minDistance = 150;
    controlsRef.current = controls;

    // 5. Build Procedural 3D Human Skull & Brain Model
    const skullGroup = new THREE.Group();
    materialsRef.current = [];

    // Main Wireframe Material
    const skullMat = new THREE.MeshBasicMaterial({
      color: wireColor,
      wireframe: true,
      transparent: true,
      opacity: wireOpacity,
    });
    materialsRef.current.push(skullMat);

    const accentMat = new THREE.MeshBasicMaterial({
      color: '#2dd4bf',
      wireframe: true,
      transparent: true,
      opacity: Math.min(1, wireOpacity * 1.5),
    });
    materialsRef.current.push(accentMat);

    const brainMat = new THREE.MeshBasicMaterial({
      color: '#10b981',
      wireframe: true,
      transparent: true,
      opacity: 0.1,
    });
    materialsRef.current.push(brainMat);

    // --- A. Cranium (Upper Skull Vault & Forehead) ---
    const craniumGeo = new THREE.IcosahedronGeometry(210, 3);
    const pos = craniumGeo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      let x = pos.getX(i);
      let y = pos.getY(i);
      let z = pos.getZ(i);

      // Forehead narrow, parietal temples wider
      if (z > 0 && y > 0) x *= 0.93;
      // Jaw taper
      if (y < 0) x *= 0.84;
      pos.setXYZ(i, x * 1.02, y * 1.18, z * 1.12);
    }
    craniumGeo.computeVertexNormals();
    const craniumMesh = new THREE.Mesh(craniumGeo, skullMat);
    craniumMesh.position.y = 30;
    skullGroup.add(craniumMesh);

    // --- B. Orbital Eye Sockets (Left & Right) ---
    const eyeSocketGeo = new THREE.TorusGeometry(38, 4, 12, 28);
    const leftEye = new THREE.Mesh(eyeSocketGeo, accentMat);
    leftEye.position.set(-62, 35, 195);
    leftEye.rotation.x = -0.15;
    skullGroup.add(leftEye);

    const rightEye = new THREE.Mesh(eyeSocketGeo, accentMat);
    rightEye.position.set(62, 35, 195);
    rightEye.rotation.x = -0.15;
    skullGroup.add(rightEye);

    // --- C. Nasal Cavity (Nose Aperture) ---
    const nasalGeo = new THREE.ConeGeometry(24, 45, 4);
    const nasalMesh = new THREE.Mesh(nasalGeo, accentMat);
    nasalMesh.rotation.x = Math.PI;
    nasalMesh.position.set(0, 5, 200);
    skullGroup.add(nasalMesh);

    // --- D. Zygomatic Arch (Cheekbones) ---
    const cheekGeo = new THREE.CylinderGeometry(15, 25, 90, 8, 2, true);
    const leftCheek = new THREE.Mesh(cheekGeo, skullMat);
    leftCheek.position.set(-110, 0, 100);
    leftCheek.rotation.z = 0.5;
    leftCheek.rotation.y = -0.4;
    skullGroup.add(leftCheek);

    const rightCheek = new THREE.Mesh(cheekGeo, skullMat);
    rightCheek.position.set(110, 0, 100);
    rightCheek.rotation.z = -0.5;
    rightCheek.rotation.y = 0.4;
    skullGroup.add(rightCheek);

    // --- E. Mandible (Jawbone Structure) ---
    const jawGeo = new THREE.CylinderGeometry(160, 95, 120, 16, 4, true);
    const jawMesh = new THREE.Mesh(jawGeo, skullMat);
    jawMesh.position.set(0, -115, 30);
    skullGroup.add(jawMesh);

    // Chin Tip Highlight
    const chinGeo = new THREE.BoxGeometry(50, 30, 40);
    const chinMesh = new THREE.Mesh(chinGeo, accentMat);
    chinMesh.position.set(0, -170, 95);
    skullGroup.add(chinMesh);

    // Teeth Arc Ridge
    const teethGeo = new THREE.TorusGeometry(65, 8, 8, 16, Math.PI);
    const teethMesh = new THREE.Mesh(teethGeo, accentMat);
    teethMesh.rotation.x = Math.PI / 2;
    teethMesh.position.set(0, -110, 110);
    skullGroup.add(teethMesh);

    // --- F. Internal Cerebral Brain Cortex Lobes ---
    const brainGroup = new THREE.Group();
    brainGroup.name = 'brainGroup';

    const leftCortexGeo = new THREE.SphereGeometry(135, 24, 24);
    leftCortexGeo.scale(0.85, 0.95, 1.25);
    const leftCortex = new THREE.Mesh(leftCortexGeo, brainMat);
    leftCortex.position.set(-60, 65, -15);
    brainGroup.add(leftCortex);

    const rightCortex = new THREE.Mesh(leftCortexGeo, brainMat);
    rightCortex.position.set(60, 65, -15);
    brainGroup.add(rightCortex);

    // Cerebellum
    const cerebellumGeo = new THREE.SphereGeometry(75, 16, 16);
    const cerebellum = new THREE.Mesh(cerebellumGeo, brainMat);
    cerebellum.position.set(0, -25, -110);
    brainGroup.add(cerebellum);

    // Glowing Core Sphere
    const coreGeo = new THREE.SphereGeometry(30, 24, 24);
    const coreMat = new THREE.MeshBasicMaterial({ color: '#2dd4bf', wireframe: true });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreMesh.position.set(0, 40, 0);
    brainGroup.add(coreMesh);

    skullGroup.add(brainGroup);

    // --- G. Cervical Spine Support ---
    const spineGeo = new THREE.CylinderGeometry(35, 45, 120, 12, 6, true);
    const spineMesh = new THREE.Mesh(spineGeo, skullMat);
    spineMesh.position.set(0, -220, -40);
    skullGroup.add(spineMesh);

    for (let i = 0; i < 4; i++) {
      const vRingGeo = new THREE.TorusGeometry(42 + i * 2, 3, 8, 20);
      const vRing = new THREE.Mesh(vRingGeo, accentMat);
      vRing.rotation.x = Math.PI / 2;
      vRing.position.set(0, -170 - i * 25, -40);
      skullGroup.add(vRing);
    }

    // --- H. Base Scanner Hologram Grid & Ring ---
    const ringGeo = new THREE.RingGeometry(280, 283, 64);
    const ringMat = new THREE.MeshBasicMaterial({
      color: wireColor,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.35,
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = Math.PI / 2;
    ringMesh.position.y = -220;
    skullGroup.add(ringMesh);

    scene.add(skullGroup);
    skullGroupRef.current = skullGroup;

    // 6. Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();

      // Pulsing effect for core
      if (coreMesh) {
        coreMesh.rotation.y += 0.01;
        coreMesh.rotation.x += 0.005;
      }

      renderer.render(scene, camera);
    };
    animate();

    // Resize Handler
    const handleResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Sync Controls Props
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = autoRotate;
      controlsRef.current.autoRotateSpeed = rotateSpeed;
    }
  }, [autoRotate, rotateSpeed]);

  // Sync Colors & Opacity
  useEffect(() => {
    materialsRef.current.forEach((mat: THREE.MeshBasicMaterial) => {
      if (mat) {
        mat.color.set(wireColor);
        mat.opacity = wireOpacity;
      }
    });
  }, [wireColor, wireOpacity]);

  // Sync Brain Core Visibility
  useEffect(() => {
    if (skullGroupRef.current) {
      const brainGroup = skullGroupRef.current.getObjectByName('brainGroup');
      if (brainGroup) {
        brainGroup.visible = showBrainCore;
      }
    }
  }, [showBrainCore]);

  return (
    <div className="w-screen h-screen bg-[#030712] text-zinc-100 flex flex-col overflow-hidden font-mono select-none">
      {/* Header Bar */}
      <header className="h-14 bg-[#09090b]/90 border-b border-[#27272a] px-6 flex items-center justify-between z-30 shadow-xl backdrop-blur">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-300 transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            ← Kembali ke Main App
          </Link>
          <div className="w-px h-5 bg-[#27272a]"></div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping"></span>
            <h1 className="text-sm font-bold tracking-widest uppercase text-cyan-400">
              STUDIO DESAIN TENGKORAK 3D (3D SKULL HOLOGRAM)
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/40 text-cyan-300">
              /desain
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs text-zinc-400">
          <span>Putar 360°: Drag Mouse</span>
          <span className="text-zinc-600">|</span>
          <span>Zoom: Scroll Wheel</span>
        </div>
      </header>

      {/* 3D Canvas Stage */}
      <div className="flex-1 relative w-full h-full">
        <div ref={mountRef} className="w-full h-full" />

        {/* Floating Controls Sidebar Panel */}
        <div className="absolute top-6 right-6 z-20 w-80 bg-[#09090b]/90 backdrop-blur border border-[#27272a] p-5 rounded-xl shadow-2xl flex flex-col gap-4 text-xs">
          <div className="flex items-center justify-between border-b border-[#27272a] pb-2">
            <span className="font-bold text-white tracking-wider uppercase flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
              SKULL 3D CONTROLLER
            </span>
          </div>

          {/* Color Picker Preset Buttons */}
          <div className="flex flex-col gap-2">
            <label className="text-zinc-400 text-[11px] font-bold">WARNA WIREFRAME HOLOGRAM:</label>
            <div className="grid grid-cols-4 gap-2">
              <button
                onClick={() => setWireColor('#06b6d4')}
                className={`h-8 rounded border transition-all cursor-pointer flex items-center justify-center ${
                  wireColor === '#06b6d4' ? 'border-white ring-2 ring-cyan-400' : 'border-transparent'
                } bg-cyan-500/30 text-cyan-300 font-bold`}
              >
                Cyan
              </button>
              <button
                onClick={() => setWireColor('#a855f7')}
                className={`h-8 rounded border transition-all cursor-pointer flex items-center justify-center ${
                  wireColor === '#a855f7' ? 'border-white ring-2 ring-purple-400' : 'border-transparent'
                } bg-purple-500/30 text-purple-300 font-bold`}
              >
                Violet
              </button>
              <button
                onClick={() => setWireColor('#10b981')}
                className={`h-8 rounded border transition-all cursor-pointer flex items-center justify-center ${
                  wireColor === '#10b981' ? 'border-white ring-2 ring-emerald-400' : 'border-transparent'
                } bg-emerald-500/30 text-emerald-300 font-bold`}
              >
                Matrix
              </button>
              <button
                onClick={() => setWireColor('#f59e0b')}
                className={`h-8 rounded border transition-all cursor-pointer flex items-center justify-center ${
                  wireColor === '#f59e0b' ? 'border-white ring-2 ring-amber-400' : 'border-transparent'
                } bg-amber-500/30 text-amber-300 font-bold`}
              >
                Amber
              </button>
            </div>
          </div>

          {/* Wireframe Opacity Slider */}
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between text-[11px]">
              <span className="text-zinc-400">INTENSITAS GLOW (OPACITY):</span>
              <span className="text-white font-bold">{Math.round(wireOpacity * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.6"
              step="0.01"
              value={wireOpacity}
              onChange={(e) => setWireOpacity(Number(e.target.value))}
              className="accent-cyan-400 cursor-pointer"
            />
          </div>

          {/* Auto Rotation Toggle */}
          <div className="flex items-center justify-between pt-1">
            <span className="text-zinc-400 text-[11px]">AUTO ROTATE 360°:</span>
            <button
              onClick={() => setAutoRotate(!autoRotate)}
              className={`px-3 py-1 rounded text-[11px] font-bold transition-all cursor-pointer ${
                autoRotate ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50' : 'bg-zinc-800 text-zinc-400'
              }`}
            >
              {autoRotate ? 'ON' : 'OFF'}
            </button>
          </div>

          {/* Rotation Speed */}
          {autoRotate && (
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between text-[11px]">
                <span className="text-zinc-400">KECEPATAN ROTASI:</span>
                <span className="text-white font-bold">{rotateSpeed}x</span>
              </div>
              <input
                type="range"
                min="0.5"
                max="5.0"
                step="0.5"
                value={rotateSpeed}
                onChange={(e) => setRotateSpeed(Number(e.target.value))}
                className="accent-cyan-400 cursor-pointer"
              />
            </div>
          )}

          {/* Show Internal Brain Core Toggle */}
          <div className="flex items-center justify-between border-t border-[#27272a] pt-3">
            <span className="text-zinc-400 text-[11px]">LOBUS OTAK DALAM (*BRAIN CORTEX*):</span>
            <button
              onClick={() => setShowBrainCore(!showBrainCore)}
              className={`px-3 py-1 rounded text-[11px] font-bold transition-all cursor-pointer ${
                showBrainCore ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50' : 'bg-zinc-800 text-zinc-400'
              }`}
            >
              {showBrainCore ? 'SHOW' : 'HIDE'}
            </button>
          </div>
        </div>

        {/* Bottom Legend */}
        <div className="absolute bottom-6 left-6 z-10 bg-[#09090b]/85 backdrop-blur border border-[#27272a] px-4 py-2.5 rounded-lg text-[10px] text-zinc-400 flex items-center gap-4">
          <span className="text-cyan-400 font-bold tracking-wider uppercase">3D SKULL HOLOGRAM WORKBENCH</span>
          <span className="text-zinc-600">|</span>
          <span>Bisa diputar 360°, di-zoom & di-customize secara live</span>
        </div>
      </div>
    </div>
  );
}
