
import { reactive } from 'vue';

class AuthState {
    init(authState) {
        Object.assign(this, authState);
    }

    isModerated() {
        return this.method === 'email';
    }
}

export const authState = reactive(new AuthState());
