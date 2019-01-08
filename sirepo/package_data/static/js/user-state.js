// jshint ignore: start
{%- if user_state %}
SIREPO.userState = {
    loginState: '{{ user_state.login_state }}',
    userName: '{{ user_state.user_name }}',
    authMethod: '{{ user_state.auth_method }}',
    displayNameSet: '{{ user_state.display_name_set }}',
};
{%- endif %}
SIREPO.IS_LOGGED_OUT = SIREPO.userState && SIREPO.userState.loginState == 'logged_out';
