// jshint ignore: start
{%- if user_state %}
SIREPO.userState = {
    loginState: '{{ user_state.login_state }}',
    userName: '{{ user_state.user_name }}',
};
{%- endif %}
SIREPO.IS_LOGGED_OUT = SIREPO.userState && SIREPO.userState.loginState == 'logged_out';
