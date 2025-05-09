
class AuthState {
    init(authState) {
        Object.assign(this, authState);
    }
}

export const authState = new AuthState();
