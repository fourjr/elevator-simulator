function clamp(x: number, min: number, max: number): number {
    /**
     * https://stackoverflow.com/a/11409944/8129786
     * Returns a number whose value is limited to the given range.
     *
     * Example: limit the output of this computation to between 0 and 255
     * (x * 255).clamp(0, 255)
     *
     * @param {Number} min The lower boundary of the output range
     * @param {Number} max The upper boundary of the output range
     * @returns A number in the range [min, max]
     * @type Number
    */
    return Math.min(Math.max(x, min), max);
};

export { clamp }