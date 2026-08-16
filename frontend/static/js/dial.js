// Smart Wardrobe - Side Dial component
// The compact vertical-swipe picker used for both the occasion dial (left)
// and season dial (right) in the kiosk view - same component, different
// value lists (see kiosk.js::dialSpec). Extracted out of KioskUI (SRP): a
// generic drag-to-pick component shouldn't live inside the kiosk's page
// controller.
//
// Gesture physics follow /mnt/skills/user/apple-design: velocity is tracked
// during the drag (not just the release position), a fast flick commits
// even under the distance threshold, and the settle motion is a real
// velocity-aware spring (damping 0.8, response 0.3 - Apple's documented
// drawer/sheet values) instead of a fixed-duration CSS easing curve, so a
// released drag keeps its own momentum into the snap.

import { triggerHaptic, animateSpring } from './utils.js';

const DISTANCE_FRACTION = 0.18; // of dial height - slow deliberate drag threshold
const VELOCITY_THRESHOLD = 400; // px/s - fast flick threshold, overrides distance

function currentTranslateY(track) {
    const transform = window.getComputedStyle(track).transform;
    if (!transform || transform === 'none') return 0;
    try {
        return new DOMMatrixReadOnly(transform).m42;
    } catch {
        return 0;
    }
}

/**
 * One dial instance. `getSpec()` is re-read on every access instead of
 * captured once, so it always reflects the controller's current language/
 * selection (icons, labels, and the selected value can all change between
 * gestures without needing to rebuild the dial).
 * @param {() => {values: string[], selected: string, dial: HTMLElement,
 *   track: HTMLElement, icon: (v:string)=>string, label: (v:string)=>string,
 *   select: (v:string, opts?:{velocity?: number}) => void}} getSpec
 */
export function createDial(getSpec) {
    let cancelSpring = null;

    function render() {
        const { track, values, selected, icon, label } = getSpec();
        if (!track) return;

        track.innerHTML = values.map(value => `
            <div class="side-dial-item ${value === selected ? 'active' : ''}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${icon(value)}</svg>
                <span>${label(value)}</span>
            </div>
        `).join('');

        updatePosition(false);
    }

    /**
     * Moves the track to reflect the current selection.
     * @param {boolean} animate - false for instant/programmatic repositions
     *   (initial render, resize, language change); true for gesture-driven
     *   settles, which get the real spring.
     * @param {number} velocity - px/s inherited from the gesture release;
     *   0 for programmatic calls (still springs smoothly, just with no
     *   initial momentum).
     */
    function updatePosition(animate = true, velocity = 0) {
        const { track, dial, values, selected } = getSpec();
        if (!track || !dial) return;

        const index = values.indexOf(selected);
        const height = dial.clientHeight || 1;
        const target = -index * height;

        track.querySelectorAll('.side-dial-item').forEach(item => {
            item.style.height = `${height}px`;
        });
        track.querySelectorAll('.side-dial-item').forEach((item, i) => {
            item.classList.toggle('active', i === index);
        });

        // Interrupt any in-flight settle and continue from its live
        // (presentation) value, never the old target - apple-design §3.
        if (cancelSpring) {
            cancelSpring();
            cancelSpring = null;
        }

        if (!animate) {
            track.classList.add('dragging'); // suppress the CSS transition, we're setting the value directly
            track.style.transform = `translateY(${target}px)`;
            return;
        }

        const from = currentTranslateY(track);
        track.classList.add('dragging'); // the spring owns the motion now, not the CSS transition
        cancelSpring = animateSpring({
            from,
            to: target,
            velocity,
            damping: 0.8,
            response: 0.3,
            onUpdate: (y) => { track.style.transform = `translateY(${y}px)`; },
            onComplete: () => {
                track.classList.remove('dragging');
                cancelSpring = null;
            },
        });
    }

    function bindGestures() {
        const { dial: container, track } = getSpec();
        if (!container || !track) return;

        let startY = 0;
        let dragging = false;
        let height = 0;
        let index = 0;
        let history = []; // {t, y} samples for release velocity (apple-design §2)

        const velocityOf = () => {
            if (history.length < 2) return 0;
            const first = history[0];
            const last = history[history.length - 1];
            const dt = (last.t - first.t) / 1000;
            return dt > 0 ? (last.y - first.y) / dt : 0;
        };

        const onStart = (clientY) => {
            if (cancelSpring) {
                cancelSpring();
                cancelSpring = null;
            }
            const spec = getSpec();
            dragging = true;
            startY = clientY;
            history = [{ t: performance.now(), y: clientY }];
            height = container.clientHeight || 1;
            index = spec.values.indexOf(spec.selected);
            track.classList.add('dragging');
        };
        const onMove = (clientY) => {
            if (!dragging) return;
            history.push({ t: performance.now(), y: clientY });
            if (history.length > 5) history.shift();
            const delta = clientY - startY;
            track.style.transform = `translateY(${-index * height + delta}px)`;
        };
        const onEnd = (clientY) => {
            if (!dragging) return;
            dragging = false;
            const delta = clientY - startY;
            const velocity = velocityOf();
            const distanceThreshold = height * DISTANCE_FRACTION;
            const commits = Math.abs(delta) >= distanceThreshold || Math.abs(velocity) > VELOCITY_THRESHOLD;
            const goingUp = (Math.abs(velocity) > VELOCITY_THRESHOLD ? velocity : delta) < 0;
            const { values, select } = getSpec();

            if (commits && goingUp && index < values.length - 1) {
                triggerHaptic('light');
                select(values[index + 1], { velocity });
            } else if (commits && !goingUp && index > 0) {
                triggerHaptic('light');
                select(values[index - 1], { velocity });
            } else {
                updatePosition(true, velocity);
            }
        };

        container.addEventListener('touchstart', (e) => onStart(e.touches[0].clientY), { passive: true });
        container.addEventListener('touchmove', (e) => onMove(e.touches[0].clientY), { passive: true });
        container.addEventListener('touchend', (e) => onEnd(e.changedTouches[0].clientY), { passive: true });

        container.addEventListener('pointerdown', (e) => {
            if (e.pointerType === 'touch') return;
            container.setPointerCapture(e.pointerId);
            onStart(e.clientY);
        });
        container.addEventListener('pointermove', (e) => {
            if (e.pointerType === 'touch') return;
            onMove(e.clientY);
        });
        container.addEventListener('pointerup', (e) => {
            if (e.pointerType === 'touch') return;
            onEnd(e.clientY);
        });

        window.addEventListener('resize', () => updatePosition(false));
    }

    return { render, updatePosition, bindGestures };
}
