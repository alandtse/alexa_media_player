# Changelog

<!--next-version-placeholder-->

## v3.8.4 (2021-03-12)
### Fix
* Handle non-json domainAttributes in activities ([`05025cf`](https://github.com/custom-components/alexa_media_player/commit/05025cf2ab23a33eed1f0a4f47ab2a4a9c50b323))
* Handle case when hass has no detectable url ([`3796a85`](https://github.com/custom-components/alexa_media_player/commit/3796a857fe9841b345f4c24a3e38f2a7086a777a))

## v3.8.3 (2021-03-11)
### Fix
* Ignore typerrors for update_last_called ([`c2c57ed`](https://github.com/custom-components/alexa_media_player/commit/c2c57eda15b6d090d129ee0bb7c5c640787bd71e))

## v3.8.2 (2021-02-20)
### Fix
* Bump alexapy==1.24.2 ([`9489268`](https://github.com/custom-components/alexa_media_player/commit/9489268a3dd469df5767a263e9d6f61644ac62d2))
* Ignore PUSH_LIST_CHANGE ([`d1737fe`](https://github.com/custom-components/alexa_media_player/commit/d1737fee541c8642967486420fc9643b660d5f56))

## v3.8.1 (2021-02-15)
### Fix
* Use external hass url as default for proxy ([`aa8df7e`](https://github.com/custom-components/alexa_media_player/commit/aa8df7e94db696977eec8dc0c85c0dabea18df74))
* Wrap calls to alexapi in async_create_task ([`0445b72`](https://github.com/custom-components/alexa_media_player/commit/0445b7227b2994b9e6dcf2bbc1b95fc203e569c2))

### Documentation
* Update badges ([`2081e0f`](https://github.com/custom-components/alexa_media_player/commit/2081e0f9075aa9706f5fab7fe0494382e7c4337c))

## v3.8.0 (2021-02-08)
### Feature
* Add name and entity_id to notification_event ([`9c6f6f8`](https://github.com/custom-components/alexa_media_player/commit/9c6f6f875c769524ba3f7b7a34f414029acc11b7))

### Fix
* Fix https proxy login ([`f873721`](https://github.com/custom-components/alexa_media_player/commit/f873721f2df741240f0a2120ecd432e2ee762edd))

### Refactor
* Remove unused lock ([`3ba2b6f`](https://github.com/custom-components/alexa_media_player/commit/3ba2b6ffac6df782305a27f1db578b3f61622d86))

## v3.7.0 (2021-02-07)
### Feature
* Use HA view for proxy address ([`3eb09ea`](https://github.com/custom-components/alexa_media_player/commit/3eb09ea0834f36178c8fd11423c0202760d96c02))

## v3.6.4 (2021-02-03)
### Fix
* Update last_update before notify update ([`77223a9`](https://github.com/custom-components/alexa_media_player/commit/77223a9b6f89cfa3bc9a4102151181c6a7b22f4d))
* Add version to manifest.json ([`faef7a1`](https://github.com/custom-components/alexa_media_player/commit/faef7a1bedfc5cec2f1415294afdf7f9276851bd))

## v3.6.3 (2021-01-28)
### Fix
* Bump to alexapy 1.22.3 ([`c3df546`](https://github.com/custom-components/alexa_media_player/commit/c3df54653318f8416ec66d7d56d421df3e3e2b2d))
* Cancel proxy after 10 minutes ([`d818f48`](https://github.com/custom-components/alexa_media_player/commit/d818f481981f63dcb620e1c554cf2fb4a65e8d87))
* Check for valid ha url ([`1b21b4a`](https://github.com/custom-components/alexa_media_player/commit/1b21b4a92888304c7f750a560f1d2a953c6509d5))
* Add otp confirmation step for proxy ([`c82d3f1`](https://github.com/custom-components/alexa_media_player/commit/c82d3f1d87e854ff6402af327a9c2624692672c1))
* Provide warning for invalid built-in 2fa key ([`af86368`](https://github.com/custom-components/alexa_media_player/commit/af863689f53993939296faeacd06516f5cd8bd04))

### Refactor
* Move translation directory ([`cd2a39a`](https://github.com/custom-components/alexa_media_player/commit/cd2a39a16223b69dc1afcef830aa005d190fc2d7))

## v3.6.2 (2021-01-24)
### Fix
* Add delay on consecutive service updates ([`7ec02a8`](https://github.com/custom-components/alexa_media_player/commit/7ec02a8761bf5361eaef70a347acdacac62119d7))
* Fix missing target devices ([`a2fff11`](https://github.com/custom-components/alexa_media_player/commit/a2fff116448427fe8074899fff28f15364448b9a))

## v3.6.1 (2021-01-24)
### Fix
* Fix announce for second account ([`14c9a12`](https://github.com/custom-components/alexa_media_player/commit/14c9a1263a90f2ed73e8dd284e6b10150ffda533))

## v3.6.0 (2021-01-24)
### Feature
* Add last_called notify service target ([`d3e35c2`](https://github.com/custom-components/alexa_media_player/commit/d3e35c24d2a6fd017ba1b53d3f7ce468f67c5f6c))

### Fix
* Fix deregistration for duplicate HA uuids ([`556d771`](https://github.com/custom-components/alexa_media_player/commit/556d77109d451e81aefba961bd1a8ac31be132de))
* Update last_called only if changed ([`545783a`](https://github.com/custom-components/alexa_media_player/commit/545783a42e88e54479587ff22bccac3b439f879b))

## v3.5.2 (2021-01-23)
### Fix
* Bump alexapy to 1.22.2 ([`fe97afe`](https://github.com/custom-components/alexa_media_player/commit/fe97afe43972acdbffe8d5ce47effc9e82a0b337))
* Fix abort message on login failure ([`c367a6e`](https://github.com/custom-components/alexa_media_player/commit/c367a6e7224f58496658f6232d972f66693a80f8))
* Fix config flow abort with failed proxy login ([`07c0868`](https://github.com/custom-components/alexa_media_player/commit/07c08685d062f1c92ffea5426feba998bbb18990))

## v3.5.1 (2021-01-23)
### Fix
* Handle amazon malformed activities output ([`62c3180`](https://github.com/custom-components/alexa_media_player/commit/62c3180f7673a6de10f1da5548c9e2e9ecf81181))
* Fix target matching for secondary accounts ([`2e66fbd`](https://github.com/custom-components/alexa_media_player/commit/2e66fbd73d601bec850ae212fa09b927a9999688))

### Documentation
* Update localization ([`617d03e`](https://github.com/custom-components/alexa_media_player/commit/617d03e6093feadfb508a019f1b1067adb40d44b))

### Refactor
* Remove unused random dependency ([`2729ca6`](https://github.com/custom-components/alexa_media_player/commit/2729ca6de8fb23ec00458746161e3851b18ba9b5))

## v3.5.0 (2021-01-18)
### Feature
* Add ability to select non-oauth login ([`8f78709`](https://github.com/custom-components/alexa_media_player/commit/8f78709b0d0511f4f0c99c9e8c5f27cd9b476c0a))
* Add last_called_summary attribute ([`79f23f7`](https://github.com/custom-components/alexa_media_player/commit/79f23f7f80e591d52b508d152049f056b6ae7427))
* Enable proxy logins ([`80114ee`](https://github.com/custom-components/alexa_media_player/commit/80114eee7a137fe904448fc34ef8e8fcf4c597f6))

### Fix
* Change to single notify service ([`2298d51`](https://github.com/custom-components/alexa_media_player/commit/2298d5127791312220d7f3306e293e3769215e09))
* Add auto submit limit for valid email error ([`18558aa`](https://github.com/custom-components/alexa_media_player/commit/18558aa5989a32c73d79a2b46fa0c37ab3605e83))
* Register events after initial setup ([`4a8fa41`](https://github.com/custom-components/alexa_media_player/commit/4a8fa41eb7e21269dcdb2464c6261224bf184bbb))
* Fix oauth processing for login ([`43d5432`](https://github.com/custom-components/alexa_media_player/commit/43d5432483a3512eaefac5e3049064e6c636876a))
* Iterate uuid for multiple accounts ([`16d7acf`](https://github.com/custom-components/alexa_media_player/commit/16d7acf95c99fc487b291488c4d32386ee08672a))
* Fix entity name for unload ([`717b7f7`](https://github.com/custom-components/alexa_media_player/commit/717b7f7fea9a6cd8a990b750e35d76a5220a17ac))
* Fix unbound alexa_client use case ([`9c0a686`](https://github.com/custom-components/alexa_media_player/commit/9c0a6864ff054b508ada390b00a4d49091f5eff8))
* Fix key errors from unloading ([`bf6e613`](https://github.com/custom-components/alexa_media_player/commit/bf6e6130d4745d4f27e0bd3eb869d9a373c13f62))
* Add changing unique_id for secondary accounts ([`fbd1e12`](https://github.com/custom-components/alexa_media_player/commit/fbd1e127b1db6a6dd812be514df23f7efe86b447))
* Check for existence of data before unload ([`5001e94`](https://github.com/custom-components/alexa_media_player/commit/5001e94cba0d45bc4e69b2c5d428ce693476bb0a))
* Fix type error for solo components ([`3c99f03`](https://github.com/custom-components/alexa_media_player/commit/3c99f03cbecb1194433d24678b5f6ae348998f60))
* Add lock entry ([`dad2a17`](https://github.com/custom-components/alexa_media_player/commit/dad2a178ce68d5abf74a0011c5d90d60bfdbcf27))
* Add logic to avoid reloading config entry ([`5f7cb1d`](https://github.com/custom-components/alexa_media_player/commit/5f7cb1dc79cfb1ecf38ff022c5d784e0db9fad36))
* Allow resuming of login session after testing ([`252e133`](https://github.com/custom-components/alexa_media_player/commit/252e13309c7599c41b8f089992be30629793897b))
* Fix detection of action required page ([`c082938`](https://github.com/custom-components/alexa_media_player/commit/c0829382bdaced90a19ba8b889340df4221540da))
* Allow proxy for action_required ([`6bd1c64`](https://github.com/custom-components/alexa_media_player/commit/6bd1c64467b2eb1acc6dcd11e060f41bdd70f27b))
* Pop hass_url ([`d671288`](https://github.com/custom-components/alexa_media_player/commit/d671288429783a867414c85e911c7356c4950a06))
* Add http prerequisite ([`e513187`](https://github.com/custom-components/alexa_media_player/commit/e513187d72d2f90316402acb0ce117f3c075a7b9))
* Fix otp registration to require confirmation ([`0a001f1`](https://github.com/custom-components/alexa_media_player/commit/0a001f1a25b0ad8ae44bfd9e993b0f84c4b7da79))
* Use lock to stagger account loading ([`8320df8`](https://github.com/custom-components/alexa_media_player/commit/8320df8eafae2d718348a701058848bc15949f73))

### Performance
* Remove extraneous notification call ([`b47988f`](https://github.com/custom-components/alexa_media_player/commit/b47988f86efbaf86b694c13f56e25545733fc92b))

### Refactor
* Update debug statements for consistency ([`7b88105`](https://github.com/custom-components/alexa_media_player/commit/7b88105e7b0b77e8df528fb787de825a2246bb23))
* Add debug for alarm_control_panel start ([`56671e3`](https://github.com/custom-components/alexa_media_player/commit/56671e36269b9426d049549f90c38e6190b4454a))
* Add more debugging to unload ([`173807f`](https://github.com/custom-components/alexa_media_player/commit/173807f1af766baed5c71c80694d3245fab20e25))
* Reduce number of startup log display ([`5c63951`](https://github.com/custom-components/alexa_media_player/commit/5c63951855c1fc09072e7ed9f2d462a407730423))

## v3.4.8 (2021-01-08)
### Fix
* Fix registration with amazon.com.au ([`7fff067`](https://github.com/custom-components/alexa_media_player/commit/7fff067392f66e107ab810c8b1b25fec3e6dd9bb))

## v3.4.7 (2021-01-06)
### Fix
* Change coordinator update to null operation ([`dfc53cc`](https://github.com/custom-components/alexa_media_player/commit/dfc53cc50376e1a480cace18cd0abf776cb1d3fd))

## v3.4.6 (2021-01-06)
### Fix
* Fix cookie exchange during oauth refresh ([`d508a0c`](https://github.com/custom-components/alexa_media_player/commit/d508a0caa60073d6ce78ce1887b0f78c7176c6e0))
* Allow devices with notification capability ([`0b88157`](https://github.com/custom-components/alexa_media_player/commit/0b88157d367f015073a9dae52e58aa2fea4ae911))
* Use sync callback for update coordinator ([`2185a86`](https://github.com/custom-components/alexa_media_player/commit/2185a86ff0bb278609993e8f00092e5c389f6634))
* Create login if login session closed ([`47bbfc4`](https://github.com/custom-components/alexa_media_player/commit/47bbfc4dfb793ea1fc8cc7e94003105ba3144e22))
* Catch login error on guard init ([`d8c5399`](https://github.com/custom-components/alexa_media_player/commit/d8c5399f8906f30e963646a408fb96444687025b))
* Fix keyerror unloading config_flows ([`23f5aff`](https://github.com/custom-components/alexa_media_player/commit/23f5aff1f4e99c4cd5b2076b099c4dfb148080d2))
* Fix multie account reauth notification ([`af9aaae`](https://github.com/custom-components/alexa_media_player/commit/af9aaae3f3914629cba37e68609720c4b8f000b6))
* Fix events processing to be account specific ([`81a87c4`](https://github.com/custom-components/alexa_media_player/commit/81a87c453402e678b02c26b288cd9d3c4cb2c374))
* Fix erroneous available on websocket event ([`5860905`](https://github.com/custom-components/alexa_media_player/commit/5860905f9acab231cb5b9e0f5adf5932ca7bdaa7))

## v3.4.5 (2021-01-02)
### Fix
* Fix generation of deviceid for oauth signin ([`1e3a362`](https://github.com/custom-components/alexa_media_player/commit/1e3a3623f79f05be0a3518bf4b112032a326c968))
* Show login failure with error page detection ([`4574e00`](https://github.com/custom-components/alexa_media_player/commit/4574e0058dac31f0377a5f7fc4024b9592cdba19))

### Refactor
* Reduce number of automatic otp retries ([`d8a63f8`](https://github.com/custom-components/alexa_media_player/commit/d8a63f808d4c77bf7870cceca23d9ce77943557b))

## v3.4.4 (2021-01-01)
### Fix
* Ensure string type for configflow ([`71b26a6`](https://github.com/custom-components/alexa_media_player/commit/71b26a6fa6c8fb8b36aaa19eeb9729702d377597))

## v3.4.3 (2021-01-01)
### Fix
* Fix oauth for non-.com domains ([`c1e5176`](https://github.com/custom-components/alexa_media_player/commit/c1e51763458f24e42082f76c4a5224146f2bb47b))
* Fix key error ([`1b2b060`](https://github.com/custom-components/alexa_media_player/commit/1b2b0602438a107c34e84a130c5f042d63b76a12))
* Allow registration in multiple HA instances ([`0a35cde`](https://github.com/custom-components/alexa_media_player/commit/0a35cde62afd14682fa5c4a7b148236d7531b0c0))
* Ignore devices without music capability ([`b9df09d`](https://github.com/custom-components/alexa_media_player/commit/b9df09d34b7c6c20686bc4e68b4b651a88dd6943))
* Check flow existence prior to unload ([`be6ab00`](https://github.com/custom-components/alexa_media_player/commit/be6ab009165937ce97704e966be1eaa1cac61b05))
* Address empty filter list for switch ([`2c10744`](https://github.com/custom-components/alexa_media_player/commit/2c107441c84d8768c5faf987b1400fa0db700e20))

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
