/**
 * Holds singleton instances which can survive an HMR reload.
 */
class Singleton {
    #values = {};

    add(name, callConstructor) {
        if (this.#values[name]) {
            return this.#values[name];
        }
        this.#values[name] = callConstructor();
        return this.#values[name];
    }
}

export const singleton = new Singleton();
