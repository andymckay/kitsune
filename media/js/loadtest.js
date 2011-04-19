/**
 * JavaScript load tests.
 *
 * Tests _must_ be behind some tunable flag or switch.
 */
(function() {
    /**
     * Hit the usernames autocomplete API with a random request
     * every few seconds. This is tuned with the
     * 'usernames-test' sample in Waffle.
     */
    function loadTestUsernamesAPI() {
        if ($('body').attr('data-usernames-test') == 'true') {
            var chars = 'abcdefghijklmnopqrstuvwxyz';
            setInterval(function() {
                var a = Math.floor(Math.random() * chars.length),
                    b = Math.floor(Math.random() * chars.length),
                    prefix = chars.substring(a, a+1) + chars.substring(b, b+1);
                $.get($('body').data('usernames-api'), {'u': prefix});
            }, 20000);
        }
    }
    $(document).ready(loadTestUsernamesAPI);
})();
