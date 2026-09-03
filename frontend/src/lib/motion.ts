import type { Transition, Variants } from "motion/react";

/**
 * Margin's motion language.
 *
 * Every value here was chosen against one question: does this help someone
 * understand what just changed? Panels and drawers use a decelerating cubic so
 * they arrive without a bounce — this is a professional tool, and overshoot on
 * a compliance control reads as unserious. Springs are reserved for the few
 * objects that are meant to feel physical: the Margin rail, dragged cards, the
 * go/no-go gate, and the wax seal.
 */

/** Panels, drawers, the Margin rail sliding in. */
export const editorial: Transition = {
  duration: 0.26,
  ease: [0.32, 0.72, 0, 1],
};

/** Small state changes: chips, badges, hover affordances. */
export const brisk: Transition = {
  duration: 0.16,
  ease: [0.32, 0.72, 0, 1],
};

/** Content settling into place after it arrives. */
export const settle: Transition = {
  duration: 0.34,
  ease: [0.16, 1, 0.3, 1],
};

/** Physical objects only. Critically damped — no visible wobble. */
export const physical: Transition = {
  type: "spring",
  stiffness: 420,
  damping: 38,
  mass: 0.9,
};

/** The one place a little weight is welcome: the wax seal landing. */
export const stamp: Transition = {
  type: "spring",
  stiffness: 620,
  damping: 26,
  mass: 1.1,
};

export const dragTransition: Transition = {
  type: "spring",
  stiffness: 520,
  damping: 42,
};

/** Findings settle in ~28ms apart, like type being set line by line. */
export const staggerList = (stagger = 0.028, delay = 0.04): Variants => ({
  hidden: {},
  visible: {
    transition: { staggerChildren: stagger, delayChildren: delay },
  },
});

export const listItem: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: settle },
};

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: settle },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: editorial },
};

export const railVariants: Variants = {
  hidden: { x: 24, opacity: 0 },
  visible: { x: 0, opacity: 1, transition: physical },
  exit: { x: 16, opacity: 0, transition: { duration: 0.18, ease: [0.4, 0, 1, 1] } },
};

export const overlayVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: brisk },
  exit: { opacity: 0, transition: brisk },
};

export const popVariants: Variants = {
  hidden: { opacity: 0, y: -4, scale: 0.985 },
  visible: { opacity: 1, y: 0, scale: 1, transition: editorial },
  exit: { opacity: 0, y: -2, scale: 0.99, transition: { duration: 0.14 } },
};
