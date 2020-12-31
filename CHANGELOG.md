# Changelog

<!--next-version-placeholder-->

## v3.4.2 (2020-12-31)
### Fix
* Add oauth token refresh ([`77e9d6c`](https://github.com/custom-components/alexa_media_player/commit/77e9d6c5d5f5ae5e2612e728fb704db18ddb772c))
* Fix handling of lack of bluetooth_state ([`980b530`](https://github.com/custom-components/alexa_media_player/commit/980b530a5fb97c9d93610225e51edd4eaa89c049))

### Documentation
* Update localization ([`ab8f4c4`](https://github.com/custom-components/alexa_media_player/commit/ab8f4c4782ba918cfbc47e1afd918f2527e10a99))

## v3.4.1 (2020-12-12)
### Fix
* Bump alexapy to 1.17.2 ([`a1606b7`](https://github.com/custom-components/alexa_media_player/commit/a1606b79227fe57ca1b9c181bade9767077c234a))
* Prevent websocket reconnection on login error ([`8c5f7bc`](https://github.com/custom-components/alexa_media_player/commit/8c5f7bc00ce1b29a04752fb8cf3ace8f286307e0))
* Fix saving of otp_secret during relogin ([`efb2e37`](https://github.com/custom-components/alexa_media_player/commit/efb2e3785ab17f4eff1529d01cc43d3d32b4bed6))
* Fix ui update of unavailable devices ([`2041c77`](https://github.com/custom-components/alexa_media_player/commit/2041c774c9c376a65c35abf074735b574cbbfb60))
* Add 2fa key error checking ([`c3cb200`](https://github.com/custom-components/alexa_media_player/commit/c3cb200df1c2f2a69109c46f0e631cfa40aa5ed9))
* Bump alexapy to 1.17.1 ([`62231e1`](https://github.com/custom-components/alexa_media_player/commit/62231e18fed9b8f150a38d840f782e4e71118ccd))

### Refactor
* Refactor test for login status success ([`7f4da8a`](https://github.com/custom-components/alexa_media_player/commit/7f4da8a452d9d07a5d40069ca749f5c6777f8e12))

## v3.4.0 (2020-12-05)
### Feature
* Add custom command support ([`9394143`](https://github.com/custom-components/alexa_media_player/commit/93941432acce6f2915e53aff212049e540a513a2))

## v3.3.1 (2020-11-29)
### Fix
* Fix key error on otp_secret ([`b07a722`](https://github.com/custom-components/alexa_media_player/commit/b07a722776d7a0b288e2b84636f644119ca5da1c))

## v3.3.0 (2020-11-27)
### Feature
* Add automatic relogin ([`23c44c3`](https://github.com/custom-components/alexa_media_player/commit/23c44c3b2b6f60b936a368a1fde2c9c6e4511d59))
* Add built-in 2FA generator ([`a025774`](https://github.com/custom-components/alexa_media_player/commit/a025774801aee5ba15a522246f269a12a2eda335))

### Fix
* Clean up cookie file input handling ([`b04274f`](https://github.com/custom-components/alexa_media_player/commit/b04274fc5556a1e99dd0de6fb524e98404a76478))

### Documentation
* Update localization ([`d07176a`](https://github.com/custom-components/alexa_media_player/commit/d07176acf39f3ddace45908e97b69597684b2628))

## v3.2.3 (2020-11-21)
### Fix
* Convert reminder alarmTime when float ([`da8b724`](https://github.com/custom-components/alexa_media_player/commit/da8b724aa8c5d494854575103005320159702d10))

### Documentation
* Fix wiki link in README.md (#995) ([`96435b9`](https://github.com/custom-components/alexa_media_player/commit/96435b96b351a137f10aea31a548041902bb169e))
* Update localization ([`9702cfb`](https://github.com/custom-components/alexa_media_player/commit/9702cfbc67e2f65d4c44b88b2a73e08018d72647))

## v3.2.2 (2020-10-11)
### Fix
* Stop refresh on disabled entities ([`db3fa9c`](https://github.com/custom-components/alexa_media_player/commit/db3fa9c3d8afd55be2d094667110c8ac825a227f))

## v3.2.1 (2020-10-02)
### Fix
* Delay processing until added to hass ([`235e718`](https://github.com/custom-components/alexa_media_player/commit/235e7189480bd2813734e8c7e060ae5d2033778f))

## v3.2.0 (2020-10-02)
### Feature
* Add notification events ([`6332750`](https://github.com/custom-components/alexa_media_player/commit/63327507e9bbfe9a313b16ed868924da64ad7322))
* Add process_timestamp attribute to notification sensors (#966) ([`c4a6df5`](https://github.com/custom-components/alexa_media_player/commit/c4a6df597831ae472d5d086d6ebc6ae4ed0258f7))
* Add timer for play_music ([`801bb80`](https://github.com/custom-components/alexa_media_player/commit/801bb80f11dc8ca05d2886e717431a1bbcabbbf8))

### Fix
* Improve dnd sync ([`5805a0b`](https://github.com/custom-components/alexa_media_player/commit/5805a0b14293300c584b4a18322befa1cfecf0fe))
* Allow switches to poll to sync ([`3304726`](https://github.com/custom-components/alexa_media_player/commit/330472620fd8b80707716d9eb2830354ddb4c1d0))
* Update ha state even if skip_api called ([`9ea414b`](https://github.com/custom-components/alexa_media_player/commit/9ea414bad449796b68109d822b1a7cc084e9e6d8))
* Refresh media players with main update ([`d28213a`](https://github.com/custom-components/alexa_media_player/commit/d28213a59201b11d1684d3368087ce3000ba062c))
* Save cookies_txt into configuration ([`c74824e`](https://github.com/custom-components/alexa_media_player/commit/c74824eaf5f5caaf0635b99929964b6c36378e96))
* Ignore PUSH_DEVICE_SETUP_STATE_CHANGE ([`56e020f`](https://github.com/custom-components/alexa_media_player/commit/56e020f35cba4e845ce5a5b881d18916f990bb2d))

### Performance
* Memoize notification state ([`4b71769`](https://github.com/custom-components/alexa_media_player/commit/4b71769e58dc47f5466d18060e8aece7bd6d9f98))

### Refactor
* Reduce false positive for dnd changes ([`079b554`](https://github.com/custom-components/alexa_media_player/commit/079b55436c9dae4ff1a83bfacd958cc7f1cd5380))
* Update logs to be more clear ([`9bfb96e`](https://github.com/custom-components/alexa_media_player/commit/9bfb96ee3554b46e5652e4a4cf5305a653771a7d))
* Remove unused _state variable ([`26c5ac3`](https://github.com/custom-components/alexa_media_player/commit/26c5ac3aff9e276d30d3f9edbdc680b7c792ca25))
* Switch to self.async_write_ha_state() ([`634a7a9`](https://github.com/custom-components/alexa_media_player/commit/634a7a917ea0dabd043bd2c8465c94b9e80669f2))

## v3.1.2 (2020-09-28)
### Fix
* Bump to alexapy 1.15.2 ([`c384110`](https://github.com/custom-components/alexa_media_player/commit/c384110acdef9d708c00e9c5c78d1177f4b59d93))
