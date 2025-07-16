
import { reactive } from 'vue';
import { schema } from '@/services/schema.js';
import { singleton } from '@/services/singleton.js';
import { uri } from '@/services/uri.js';

class AuthState {
    init(authState) {
        Object.assign(this, authState);
    }

    checkNeedCompleteRegistration() {
        if (this.isLoggedIn && ! this.needCompleteRegistration) {
            uri.redirectAppRoot();
            return false;
        }
        return true;
    }

    checkNeedLogin() {
        if (this.isLoggedIn) {
            uri.redirectAppRoot();
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
            uri.redirectAppRoot();
            return;
        }
        throw new Error(
            response.error
            //TODO(pjm): support_email should be a clickable link
            || `Server reported an error, please contact ${schema.feature_config.support_email}`
        );
    }
}

export const authState = singleton.add('authState', () => reactive(new AuthState()));
