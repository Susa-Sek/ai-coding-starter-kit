# Creative Frontend Patterns

> Copy-paste ready code patterns for animations, 3D, creative layouts, and micro-interactions.

## Dependencies

```bash
# Animation
npm install framer-motion

# 3D
npm install three @react-three/fiber @react-three/drei

# Scroll
npm install lenis

# Utils
npm install clsx tailwind-merge
```

---

## 1. Animationen & Motion (Framer Motion)

### 1.1 Scroll-Triggered Animations

```tsx
import { motion, useInView } from "framer-motion"
import { useRef } from "react"

export function ScrollReveal({ children }: { children: React.ReactNode }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 50 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  )
}
```

### 1.2 Staggered List Animation

```tsx
import { motion } from "framer-motion"

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
}

export function StaggeredList({ items }: { items: string[] }) {
  return (
    <motion.ul variants={container} initial="hidden" animate="show">
      {items.map((text, i) => (
        <motion.li key={i} variants={item}>
          {text}
        </motion.li>
      ))}
    </motion.ul>
  )
}
```

### 1.3 Page Transitions

```tsx
// app/layout.tsx
import { AnimatePresence, motion } from "framer-motion"
import { usePathname } from "next/navigation"

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
```

### 1.4 Hover Effects

```tsx
import { motion } from "framer-motion"

// Scale on hover
export function ScaleHover({ children }: { children: React.ReactNode }) {
  return (
    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
      {children}
    </motion.div>
  )
}

// Glow effect
export function GlowHover({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      whileHover={{
        boxShadow: "0 0 30px rgba(99, 102, 241, 0.5)",
        borderColor: "rgba(99, 102, 241, 1)"
      }}
      className="border border-transparent rounded-lg p-4 transition-colors"
    >
      {children}
    </motion.div>
  )
}

// Magnetic button
export function MagneticButton({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.9 }}
      className="cursor-pointer"
    >
      {children}
    </motion.div>
  )
}
```

### 1.5 Text Animations

```tsx
import { motion } from "framer-motion"

// Split text animation
export function AnimatedText({ text }: { text: string }) {
  const words = text.split(" ")

  return (
    <motion.div className="flex flex-wrap gap-x-2">
      {words.map((word, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1, duration: 0.4 }}
        >
          {word}
        </motion.span>
      ))}
    </motion.div>
  )
}

// Typewriter effect
export function Typewriter({ text, speed = 50 }: { text: string; speed?: number }) {
  const [displayed, setDisplayed] = useState("")

  useEffect(() => {
    let i = 0
    const timer = setInterval(() => {
      if (i < text.length) {
        setDisplayed(text.slice(0, i + 1))
        i++
      } else {
        clearInterval(timer)
      }
    }, speed)
    return () => clearInterval(timer)
  }, [text, speed])

  return <span>{displayed}<span className="animate-pulse">|</span></span>
}

// Reveal from line
export function LineReveal({ text }: { text: string }) {
  return (
    <div className="overflow-hidden">
      <motion.p
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        {text}
      </motion.p>
    </div>
  )
}
```

---

## 2. 3D & WebGL (React Three Fiber)

### 2.1 Basic 3D Scene Setup

```tsx
"use client"

import { Canvas } from "@react-three/fiber"
import { OrbitControls, Environment } from "@react-three/drei"

export function Scene3D({ children }: { children?: React.ReactNode }) {
  return (
    <div className="w-full h-[500px]">
      <Canvas camera={{ position: [0, 0, 5] }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} />
        <Environment preset="city" />
        {children}
        <OrbitControls enableZoom={false} />
      </Canvas>
    </div>
  )
}
```

### 2.2 Interactive 3D Object (Mouse Tracking)

```tsx
"use client"

import { Canvas, useFrame } from "@react-three/fiber"
import { useRef } from "react"
import { useMouse } from "@/hooks/use-mouse"
import * as THREE from "three"

function InteractiveSphere() {
  const meshRef = useRef<THREE.Mesh>(null)
  const { x, y } = useMouse()

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.x = y * 0.5
      meshRef.current.rotation.y = x * 0.5
    }
  })

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1.5, 64, 64]} />
      <meshStandardMaterial color="#6366f1" metalness={0.8} roughness={0.2} />
    </mesh>
  )
}

export function Interactive3D() {
  return (
    <Canvas className="w-full h-[400px]">
      <ambientLight />
      <pointLight position={[10, 10, 10]} />
      <InteractiveSphere />
    </Canvas>
  )
}
```

### 2.3 Particle System

```tsx
"use client"

import { Canvas, useFrame } from "@react-three/fiber"
import { useRef, useMemo } from "react"
import * as THREE from "three"

function Particles({ count = 500 }) {
  const points = useRef<THREE.Points>(null)

  const particles = useMemo(() => {
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count * 3; i++) {
      positions[i] = (Math.random() - 0.5) * 10
    }
    return positions
  }, [count])

  useFrame((state) => {
    if (points.current) {
      points.current.rotation.y = state.clock.elapsedTime * 0.05
    }
  })

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={particles.length / 3}
          array={particles}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial size={0.02} color="#6366f1" transparent opacity={0.8} />
    </points>
  )
}

export function ParticleBackground() {
  return (
    <div className="fixed inset-0 -z-10">
      <Canvas camera={{ position: [0, 0, 5] }}>
        <Particles />
      </Canvas>
    </div>
  )
}
```

### 2.4 3D Model Loading

```tsx
"use client"

import { Canvas } from "@react-three/fiber"
import { useGLTF, OrbitControls, Environment } from "@react-three/drei"

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url)
  return <primitive object={scene} scale={1.5} />
}

export function Model3D({ modelUrl }: { modelUrl: string }) {
  return (
    <Canvas className="w-full h-[500px]">
      <Suspense fallback={null}>
        <Environment preset="studio" />
        <Model url={modelUrl} />
        <OrbitControls />
      </Suspense>
    </Canvas>
  )
}
```

---

## 3. Kreative Layouts

### 3.1 Breaking the Grid (Asymmetric)

```tsx
export function AsymmetricGrid() {
  return (
    <div className="grid grid-cols-12 gap-4 p-8">
      <div className="col-span-8 row-span-2 bg-indigo-500 rounded-2xl p-6">
        <h2 className="text-4xl font-bold">Large Feature</h2>
      </div>
      <div className="col-span-4 bg-purple-500 rounded-2xl p-6">
        <p>Side content</p>
      </div>
      <div className="col-span-4 bg-pink-500 rounded-2xl p-6">
        <p>Another side</p>
      </div>
      <div className="col-span-6 col-start-2 bg-blue-500 rounded-2xl p-6 -rotate-2">
        <p>Offset content</p>
      </div>
    </div>
  )
}
```

### 3.2 Brutalist Aesthetic

```tsx
export function BrutalistCard({ title, content }: { title: string; content: string }) {
  return (
    <div className="border-4 border-black bg-white p-6 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] transition-shadow">
      <h3 className="text-2xl font-black uppercase tracking-tight mb-4">{title}</h3>
      <p className="text-lg">{content}</p>
    </div>
  )
}

export function BrutalistButton({ children }: { children: React.ReactNode }) {
  return (
    <button className="bg-black text-white px-8 py-4 text-lg font-bold uppercase tracking-wide border-4 border-black hover:bg-white hover:text-black transition-colors">
      {children}
    </button>
  )
}
```

### 3.3 Split-Screen Layout

```tsx
export function SplitScreen() {
  return (
    <div className="flex h-screen">
      <div className="w-1/2 bg-black text-white flex items-center justify-center p-12">
        <div>
          <h1 className="text-6xl font-bold mb-4">Left Side</h1>
          <p className="text-xl text-gray-400">Fixed position content</p>
        </div>
      </div>
      <div className="w-1/2 overflow-y-auto p-12">
        {/* Scrollable content */}
        <div className="space-y-8">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-96 bg-gray-100 rounded-2xl p-8">
              Section {i}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

### 3.4 Overlapping Elements

```tsx
export function OverlappingCards() {
  return (
    <div className="relative h-[600px] p-8">
      <div className="absolute top-0 left-0 w-2/3 h-80 bg-indigo-500 rounded-2xl p-8 z-10 rotate-3">
        <h3 className="text-3xl font-bold text-white">First Card</h3>
      </div>
      <div className="absolute top-20 right-0 w-2/3 h-80 bg-purple-500 rounded-2xl p-8 z-20 -rotate-2">
        <h3 className="text-3xl font-bold text-white">Second Card</h3>
      </div>
      <div className="absolute top-40 left-1/4 w-2/3 h-80 bg-pink-500 rounded-2xl p-8 z-30 rotate-1">
        <h3 className="text-3xl font-bold text-white">Third Card</h3>
      </div>
    </div>
  )
}
```

### 3.5 Scroll-Based Layout Changes

```tsx
"use client"

import { motion, useScroll, useTransform } from "framer-motion"
import { useRef } from "react"

export function ScrollLayout() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] })

  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [0.8, 1, 0.8])
  const rotate = useTransform(scrollYProgress, [0, 1], [-5, 5])

  return (
    <section ref={ref} className="min-h-screen flex items-center justify-center">
      <motion.div
        style={{ scale, rotate }}
        className="w-2/3 h-96 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-3xl p-8"
      >
        <h2 className="text-4xl font-bold text-white">Transforms on Scroll</h2>
      </motion.div>
    </section>
  )
}
```

---

## 4. Micro-Interactions

### 4.1 Custom Cursor

```tsx
"use client"

import { motion } from "framer-motion"
import { useEffect, useState } from "react"

export function CustomCursor() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const [isHovering, setIsHovering] = useState(false)

  useEffect(() => {
    const updateMouse = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY })
    }

    const handleMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === "A" || target.tagName === "BUTTON" || target.closest("a") || target.closest("button")) {
        setIsHovering(true)
      } else {
        setIsHovering(false)
      }
    }

    window.addEventListener("mousemove", updateMouse)
    window.addEventListener("mouseover", handleMouseOver)
    return () => {
      window.removeEventListener("mousemove", updateMouse)
      window.removeEventListener("mouseover", handleMouseOver)
    }
  }, [])

  return (
    <>
      <motion.div
        className="fixed top-0 left-0 w-4 h-4 bg-white rounded-full pointer-events-none z-[9999] mix-blend-difference"
        style={{ x: mousePosition.x - 8, y: mousePosition.y - 8 }}
      />
      <motion.div
        className="fixed top-0 left-0 rounded-full border border-white pointer-events-none z-[9999] mix-blend-difference"
        animate={{
          width: isHovering ? 60 : 40,
          height: isHovering ? 60 : 40,
          x: mousePosition.x - (isHovering ? 30 : 20),
          y: mousePosition.y - (isHovering ? 30 : 20),
        }}
        transition={{ type: "spring", stiffness: 500, damping: 28 }}
      />
    </>
  )
}
```

### 4.2 Smooth Scroll (Lenis)

```tsx
"use client"

import { useEffect, useRef } from "react"
import Lenis from "lenis"

export function SmoothScroll({ children }: { children: React.ReactNode }) {
  const lenisRef = useRef<Lenis | null>(null)

  useEffect(() => {
    lenisRef.current = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    })

    function raf(time: number) {
      lenisRef.current?.raf(time)
      requestAnimationFrame(raf)
    }

    requestAnimationFrame(raf)

    return () => {
      lenisRef.current?.destroy()
    }
  }, [])

  return <>{children}</>
}
```

### 4.3 Scroll Progress Indicator

```tsx
"use client"

import { motion, useScroll, useSpring } from "framer-motion"

export function ScrollProgress() {
  const { scrollYProgress } = useScroll()
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30 })

  return (
    <motion.div
      className="fixed top-0 left-0 right-0 h-1 bg-indigo-500 origin-left z-50"
      style={{ scaleX }}
    />
  )
}
```

### 4.4 Image Reveal on Scroll

```tsx
"use client"

import { motion, useScroll, useTransform } from "framer-motion"
import { useRef } from "react"

export function ImageReveal({ src, alt }: { src: string; alt: string }) {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"]
  })

  const clipPath = useTransform(
    scrollYProgress,
    [0, 0.5],
    ["inset(100% 0% 0% 0%)", "inset(0% 0% 0% 0%)"]
  )

  return (
    <div ref={ref} className="overflow-hidden">
      <motion.img
        src={src}
        alt={alt}
        style={{ clipPath }}
        className="w-full h-auto"
      />
    </div>
  )
}
```

### 4.5 Magnetic Effect

```tsx
"use client"

import { motion, useMotionValue, useSpring } from "framer-motion"
import { useRef } from "react"

export function MagneticElement({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)

  const springX = useSpring(x, { stiffness: 150, damping: 15 })
  const springY = useSpring(y, { stiffness: 150, damping: 15 })

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    x.set(e.clientX - centerX)
    y.set(e.clientY - centerY)
  }

  const handleMouseLeave = () => {
    x.set(0)
    y.set(0)
  }

  return (
    <motion.div
      ref={ref}
      style={{ x: springX, y: springY }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="inline-block"
    >
      {children}
    </motion.div>
  )
}
```

---

## 5. Utility Hooks

### useMouse Hook

```tsx
"use client"

import { useState, useEffect } from "react"

export function useMouse() {
  const [position, setPosition] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const handleMouse = (e: MouseEvent) => {
      setPosition({
        x: (e.clientX / window.innerWidth) * 2 - 1,
        y: -(e.clientY / window.innerHeight) * 2 + 1,
      })
    }

    window.addEventListener("mousemove", handleMouse)
    return () => window.removeEventListener("mousemove", handleMouse)
  }, [])

  return position
}
```

### useScrollDirection Hook

```tsx
"use client"

import { useState, useEffect } from "react"

export function useScrollDirection() {
  const [scrollDirection, setScrollDirection] = useState<"up" | "down">("up")

  useEffect(() => {
    let lastScrollY = window.scrollY

    const updateScrollDirection = () => {
      const scrollY = window.scrollY
      const direction = scrollY > lastScrollY ? "down" : "up"
      if (direction !== scrollDirection && Math.abs(scrollY - lastScrollY) > 10) {
        setScrollDirection(direction)
      }
      lastScrollY = scrollY > 0 ? scrollY : 0
    }

    window.addEventListener("scroll", updateScrollDirection)
    return () => window.removeEventListener("scroll", updateScrollDirection)
  }, [scrollDirection])

  return scrollDirection
}
```

---

## Quick Reference

| Pattern | Library | Use Case |
|---------|---------|----------|
| Scroll Reveal | framer-motion | Content appears on scroll |
| Staggered List | framer-motion | Sequential item animations |
| Page Transitions | framer-motion | Smooth route changes |
| Hover Effects | framer-motion | Interactive feedback |
| 3D Scene | @react-three/fiber | Immersive experiences |
| Particles | @react-three/fiber | Background effects |
| Custom Cursor | framer-motion | Brand identity |
| Smooth Scroll | lenis | Premium feel |
| Scroll Progress | framer-motion | Reading indicator |
| Magnetic | framer-motion | Playful interactions |