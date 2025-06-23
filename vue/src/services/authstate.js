
import { appState } from '@/services/appstate.js';
import { reactive } from 'vue';
import { uri } from '@/services/uri.js';

class AuthState {
    init(authState) {
        Object.assign(this, authState);
    }

    checkNeedsCompleteRegistration() {
        if (this.isLoggedIn && ! this.needCompleteRegistration) {
            this.redirectAppRoot();
            return false;
        }
        return true;
    }

    checkNeedsLogin() {
        if (this.isLoggedIn) {
            this.redirectAppRoot();
            return false;
        }
        return true;
    }

    getAuthMethod() {
        if (! this.visibleMethods.length === 1) {
            throw new Error(
                `authState.visibleMethods must contain only one login method: ${this.visibleMethods}`,
            );
        }
        return this.visibleMethods[0];
    }

    handleLogin(response) {
        if (response.state === 'ok' && response.authState) {
            this.init(response.authState);
            this.redirectAppRoot();
            return;
        }
        if (response.error === 'Server Error') {
            response.error = '';
        }
        return response.error
        //TODO(pjm): support_email should be a clickable link
            || `Server reported an error, please contact ${appState.schema.feature_config.support_email}`;
    }

    isModerated() {
        return this.getAuthMethod() === 'email';
    }

    redirectAppRoot() {
        uri.redirectAppRoot();
    }
}

export const authState = reactive(new AuthState());
