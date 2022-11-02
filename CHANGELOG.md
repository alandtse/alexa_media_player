# Changelog

<!--next-version-placeholder-->

## v4.3.1 (2022-11-02)
### Fix
* **notify:** Handle null data key ([#1767](https://github.com/custom-components/alexa_media_player/issues/1767)) ([`08c2109`](https://github.com/custom-components/alexa_media_player/commit/08c2109ee24d673a7b29d1f1244569f5dee40004))

## v4.3.0 (2022-10-31)
### Feature
* Add ZigBee contact sensors support ([#1754](https://github.com/custom-components/alexa_media_player/issues/1754)) ([`cd162cb`](https://github.com/custom-components/alexa_media_player/commit/cd162cbb8ebbea5af19c0d370621c4f8e169cf5a))

## v4.2.0 (2022-10-29)
### Feature
* **notify:** Set default data `type` to `tts` ([#1739](https://github.com/custom-components/alexa_media_player/issues/1739)) ([`7027e4a`](https://github.com/custom-components/alexa_media_player/commit/7027e4a992259029a7745bc2d8b32ea08076d7da))

### Fix
* Handle None responses in clear_history ([`52b1c6e`](https://github.com/custom-components/alexa_media_player/commit/52b1c6e85b4aaa021ed5bc09f2ef6172f00b1700))
* Handle key errors due to bad alexa responses ([`5788ab8`](https://github.com/custom-components/alexa_media_player/commit/5788ab887ec621d8811936f79f1308e5948b0e92))

### Documentation
* Update localization ([`9176592`](https://github.com/custom-components/alexa_media_player/commit/9176592572a160f5af04c575079688ac12be2a2e))

## v4.1.2 (2022-09-07)
### Fix
* Check for missing hass_url during auto reauth ([`7d181a3`](https://github.com/custom-components/alexa_media_player/commit/7d181a39435cb7958d0b3ccba36e7a0ebd8eccdb))
* Fix reauth caused by bad amazon response ([`58af5b3`](https://github.com/custom-components/alexa_media_player/commit/58af5b3027d34fdcf13c16dae9e12f92671958b3))

## v4.1.1 (2022-09-05)
### Fix
* **notify:** Improve message for missing keys ([`c2ce6a4`](https://github.com/custom-components/alexa_media_player/commit/c2ce6a42caf7f9355671c4488358e318c45ff2a4))
* Fix unnecessary reauth if 500 error detected ([`a8aab6b`](https://github.com/custom-components/alexa_media_player/commit/a8aab6bfe513bf4dbec361baa5d3b60fa98c99ef))
* Ignore missing async_remove_listener ([`06626dc`](https://github.com/custom-components/alexa_media_player/commit/06626dc1455f8b6c288249544ecd8439782663a5))
* Fix temperature showing in Celsius ([#1682](https://github.com/custom-components/alexa_media_player/issues/1682)) ([`13afaa8`](https://github.com/custom-components/alexa_media_player/commit/13afaa846e3b40c364699f873b54bd4feaa8b24e))

### Documentation
* Update localization ([`5b174b7`](https://github.com/custom-components/alexa_media_player/commit/5b174b7ada550485eaa02ffb48227aa529fed72a))

## v4.1.0 (2022-07-21)
### Feature
* Allow skipping of proxy warning ([`5ed2082`](https://github.com/custom-components/alexa_media_player/commit/5ed208250f6c3e951e653fa2f88ff3345c5496ce))

### Documentation
* Update localization ([`76cfff2`](https://github.com/custom-components/alexa_media_player/commit/76cfff281cbdad9d6ef27a05b6ec9585c7e9af6f))

### Refactor
* Replace hard coded strings ([`a08cc04`](https://github.com/custom-components/alexa_media_player/commit/a08cc04754d2fa960ffe5c89812717c4683994ab))

## v4.0.3 (2022-06-26)
### Fix
* **sensor:** Inherit from SensorEntity ([`c28b8ef`](https://github.com/custom-components/alexa_media_player/commit/c28b8efd1f800b73761db6960dc97c68af71b7c3))
* Fix forced relogin using configuration.yaml ([`a006bcc`](https://github.com/custom-components/alexa_media_player/commit/a006bcc18f81ffcb1c734b77a06f9f320dbbf842))
* **notifications:** Handle new recurrence rules ([`2c70eda`](https://github.com/custom-components/alexa_media_player/commit/2c70eda500d000547970c0d2d67657bcfea0e90c))
* Bump alexapy==1.26.1 ([`56a1633`](https://github.com/custom-components/alexa_media_player/commit/56a1633fe0de965ee74b0ea217a14962fb768335))
* Address potential race condition with last_called ([`f197307`](https://github.com/custom-components/alexa_media_player/commit/f19730729413c353997f5bb5f2edff8452deacad))

### Documentation
* Update localization ([`bc0ddbb`](https://github.com/custom-components/alexa_media_player/commit/bc0ddbbecea25b5dd864782d2c7ec03cfaaa0e30))

### Refactor
* Add next_alarm label ([`33f5d4c`](https://github.com/custom-components/alexa_media_player/commit/33f5d4c2b70c976641ff419d9d791ed0970b99d7))

## v4.0.2 (2022-06-04)
### Fix
* Store and reuse mac_dms between sessions ([`d663209`](https://github.com/custom-components/alexa_media_player/commit/d6632093d39a989b705ee0f8b993abae97805819))

### Documentation
* Update localization ([`3afd369`](https://github.com/custom-components/alexa_media_player/commit/3afd369f82f10493f9a9ad3927e3bfc0dc8360cd))

## v4.0.1 (2022-05-29)
### Fix
* Remove CONF_OAUTH_LOGIN calls ([`139fded`](https://github.com/custom-components/alexa_media_player/commit/139fded9a3dcd18b78e6bcecc16034f602f4bce4))

## v4.0.0 (2022-05-29)
### Fix
* Catch httpx.ConnectError during proxy ([`96bbd55`](https://github.com/custom-components/alexa_media_player/commit/96bbd55ca99c3e314a08fe9d78e405416c0b9fcb))
* Treat lack of mac_dms as login failure ([`d7c9a8c`](https://github.com/custom-components/alexa_media_player/commit/d7c9a8ce16745c747e5b83a3e4677c9c3f747c83))
* Handle unknown recurring patterns ([`92bab7c`](https://github.com/custom-components/alexa_media_player/commit/92bab7c1ad73e9809cbab8de830aa7fb3d82bc55))
* Use non-deprecated async_get ([`113b5e2`](https://github.com/custom-components/alexa_media_player/commit/113b5e274831687563659a8163b33e5d0bb39532))
* Ignore PUSH_MEDIA_PREFERENCE_CHANGE ([`0dbcddf`](https://github.com/custom-components/alexa_media_player/commit/0dbcddfc3ed03b9c4874666d8b556e28f1102573))

### Breaking
* Legacy login and options have been removed. These options resulted in degraded operations and generated extra support requests. You will be forced to relogin if an older method is detected.  ([`ee724ab`](https://github.com/custom-components/alexa_media_player/commit/ee724ab693ef58cfc2b15d3b3eeee216b9ce7caa))

### Documentation
* Update localization ([`d5bbfd0`](https://github.com/custom-components/alexa_media_player/commit/d5bbfd09099da6f8197348ec17b50fad5d2c9410))
* Change Homeassistant to Home Assistant ([#1597](https://github.com/custom-components/alexa_media_player/issues/1597)) ([`90037ed`](https://github.com/custom-components/alexa_media_player/commit/90037edc4db536b973b7f8d23d4a28f7df47f21c))
* Update HACS url ([#1596](https://github.com/custom-components/alexa_media_player/issues/1596)) ([`d9d119a`](https://github.com/custom-components/alexa_media_player/commit/d9d119a6e8aca13bd0acf6a583ea808d2be87597))

### Refactor
* Remove legacy login options ([`ee724ab`](https://github.com/custom-components/alexa_media_player/commit/ee724ab693ef58cfc2b15d3b3eeee216b9ce7caa))

## v3.11.3 (2022-04-28)
### Fix
* Bump dependencies ([`beedc06`](https://github.com/custom-components/alexa_media_player/commit/beedc062eb67114762ce2b322e68748f6e896ee6))

### Documentation
* Update localization ([`5f2de48`](https://github.com/custom-components/alexa_media_player/commit/5f2de48b9f113f56cf0a41bcb970dbca944d6924))

## v3.11.2 (2022-04-17)
### Fix
* Reset cookies on proxy start ([#1568](https://github.com/custom-components/alexa_media_player/issues/1568)) ([`7aef24b`](https://github.com/custom-components/alexa_media_player/commit/7aef24b4d5be75fa302d9e1e12aff2b85ce057e5))
* Reset cookies on proxy start ([`f064532`](https://github.com/custom-components/alexa_media_player/commit/f06453289189adb484a9b9a003489620b05abead))

## v3.11.1 (2022-04-05)
### Fix
* Use EntityCategory enum instead of strings ([#1554](https://github.com/custom-components/alexa_media_player/issues/1554)) ([`695839c`](https://github.com/custom-components/alexa_media_player/commit/695839cbbf0a8cc51400f736c8c3d20ec99bb35b))
* Use ConfigEntryNotReady during startup ([#1557](https://github.com/custom-components/alexa_media_player/issues/1557)) ([`2b14c3b`](https://github.com/custom-components/alexa_media_player/commit/2b14c3bf65c93cd39cf9992c912b29dcc8f28fb2))

## v3.11.0 (2022-03-16)
### Feature
* Add entity_category to the AlexaMediaSwitches ([#1537](https://github.com/custom-components/alexa_media_player/issues/1537)) ([`3f42a45`](https://github.com/custom-components/alexa_media_player/commit/3f42a4577219c3ab76e50d8f956640376bdcd9d5))

### Documentation
* Update localization ([`a19d9e2`](https://github.com/custom-components/alexa_media_player/commit/a19d9e2996df9e71645ef36144f23723c17b5578))

## v3.10.15 (2021-12-03)
### Fix
* Loosen allowed versions of dependencies ([`f083f80`](https://github.com/custom-components/alexa_media_player/commit/f083f80677e644fb937ae58e739c56f8ab23d900))
* Allow beta versions of 2021.12 ([`29e2032`](https://github.com/custom-components/alexa_media_player/commit/29e2032535296add0f77beef7bba3f5649da4645))

## v3.10.14 (2021-11-23)
### Fix
* Require 2021.12.0 ([`994a2fb`](https://github.com/custom-components/alexa_media_player/commit/994a2fbfab9203d2486007fdf177f68bf6d42971))

## v3.10.13 (2021-11-23)
### Fix
* Fix key error if entry exists ([`4f2a2b2`](https://github.com/custom-components/alexa_media_player/commit/4f2a2b2f328ec4855be1848c4889b1c513e99fd1))
* Bump deps ([`f6fb70b`](https://github.com/custom-components/alexa_media_player/commit/f6fb70b467033c7f1da3f94c01655253d2c0dd56))
* Handle deprecation of device_state_attributes ([`c224ee4`](https://github.com/custom-components/alexa_media_player/commit/c224ee4af0bff57efc89b6f8a9707b10ff548538))

## v3.10.12 (2021-11-19)
### Fix
* Fix conversion of aiohttp cookie to httpx ([`598175f`](https://github.com/custom-components/alexa_media_player/commit/598175f3e8297aea256a22417565df79638c1d8b))
* Set default `accounts` key in dictionary ([`ac4d3f9`](https://github.com/custom-components/alexa_media_player/commit/ac4d3f93db2249c16a02fe64d0b3a78e68cd039c))

## v3.10.11 (2021-11-16)
### Fix
* Bump alexapy to 1.25.2 ([`7de579d`](https://github.com/custom-components/alexa_media_player/commit/7de579d2fbd6fff7fb8a4196a5e79e8a65a31b44))
* Bump alexapy to 1.25.2 ([`f41c8fe`](https://github.com/custom-components/alexa_media_player/commit/f41c8fe9a94150cd37311aaff845ad5511cdf881))

## v3.10.10 (2021-10-13)
### Fix
* Fix issue where next_alarm would cancel on reload ([#1379](https://github.com/custom-components/alexa_media_player/issues/1379)) ([`a5dd83a`](https://github.com/custom-components/alexa_media_player/commit/a5dd83a3ab1a7bec565e470e11d28d3d5076b695))

## v3.10.9 (2021-10-13)
### Fix
* Fix icon on do not disturb switch ([#1377](https://github.com/custom-components/alexa_media_player/issues/1377)) ([`5407be3`](https://github.com/custom-components/alexa_media_player/commit/5407be36fd4e34782224212af5659a63d9dc306a))

### Documentation
* Update localization ([`a30af11`](https://github.com/custom-components/alexa_media_player/commit/a30af11fa5a8cd6848401023597b4be96d6c1104))

## v3.10.8 (2021-08-03)
### Fix
* Fix color mapping during color conversion ([#1345](https://github.com/custom-components/alexa_media_player/issues/1345)) ([`c296aef`](https://github.com/custom-components/alexa_media_player/commit/c296aefed824f0ba8acde166a4a43bf29c6f9cd8))
* Parse timezone from timestamp ([`c7dc5f2`](https://github.com/custom-components/alexa_media_player/commit/c7dc5f27082e253903fd596d86947dcfd7c80cc5))

### Documentation
* Update localization ([`d1ece99`](https://github.com/custom-components/alexa_media_player/commit/d1ece992d5fdf8e5c7934d0db7c5f21a05707ea8))

## v3.10.7 (2021-07-15)
### Fix
* Fix comparison between offset-naive and offset-aware datetimes (#1338) ([#1339](https://github.com/custom-components/alexa_media_player/issues/1339)) ([`bcc996a`](https://github.com/custom-components/alexa_media_player/commit/bcc996a6088a0c2826d828cdb114f36abcf69ee9))
* Fix comparison between offset-naive and offset-aware datetimes ([#1338](https://github.com/custom-components/alexa_media_player/issues/1338)) ([`0ccdb18`](https://github.com/custom-components/alexa_media_player/commit/0ccdb181c52f61f221eb50aad0fc2ad97b71b59f))

## v3.10.6 (2021-06-16)
### Fix
* Use timezone aware datetime for timers ([`de4a962`](https://github.com/custom-components/alexa_media_player/commit/de4a96230828e7226fb6c58461f983210892ca10))
* Handle unknown recurrence patterns ([`a7a173c`](https://github.com/custom-components/alexa_media_player/commit/a7a173c4f82500eeb0a3525990777665920790ad))

### Documentation
* Update localization ([`9e8f7d9`](https://github.com/custom-components/alexa_media_player/commit/9e8f7d90084c88473e3449be11971d694e6953d6))

## v3.10.5 (2021-05-18)
### Fix
* Avoid pruning devices in secondary accounts ([`a62a371`](https://github.com/custom-components/alexa_media_player/commit/a62a3710aee48e2ddb0ab72ca491384b1d95e597))

### Documentation
* Update localization ([`d368377`](https://github.com/custom-components/alexa_media_player/commit/d3683774e07e10c9416f189b8f7d654e33957b5b))

## v3.10.4 (2021-05-15)
### Fix
* Handle case where alexa guard is disabled ([#1297](https://github.com/custom-components/alexa_media_player/issues/1297)) ([`6295e93`](https://github.com/custom-components/alexa_media_player/commit/6295e93a0761da1365f761a56e2d29d125998f9a))

### Documentation
* Update localization ([`e148ae4`](https://github.com/custom-components/alexa_media_player/commit/e148ae40219a0610a6e401dd97e81aaec75ba531))
* Update localization ([`fb952ca`](https://github.com/custom-components/alexa_media_player/commit/fb952cadc34a47aaf4dba1d2760cf4d0ee5a54e4))

## v3.10.3 (2021-05-15)
### Fix
* Update entity state after network discovery (#1291) ([#1295](https://github.com/custom-components/alexa_media_player/issues/1295)) ([`b2302ec`](https://github.com/custom-components/alexa_media_player/commit/b2302ec16da19657bc1dfd7c6cd0b4343c7404db))
* Update entity state after network discovery ([#1291](https://github.com/custom-components/alexa_media_player/issues/1291)) ([`9804dd3`](https://github.com/custom-components/alexa_media_player/commit/9804dd35188befb7e1053369f7a6fa6befa1e860))

## v3.10.2 (2021-05-13)
### Fix
* Prune devices removed from amazon ([`f75f8b9`](https://github.com/custom-components/alexa_media_player/commit/f75f8b92253e256f727f1f75c6516460a7774327))

### Documentation
* Update localization ([`74ec44b`](https://github.com/custom-components/alexa_media_player/commit/74ec44b00334e91678541c2c2b096ea022294e86))

## v3.10.1 (2021-05-08)
### Fix
* Improve checking for skill backed appliances #1277 ([`ea04bae`](https://github.com/custom-components/alexa_media_player/commit/ea04bae4968df557fd6e8fab6b0745bae04b807c))

### Documentation
* Update localization ([`7041760`](https://github.com/custom-components/alexa_media_player/commit/7041760701a3d9acb3b35f82a3cb84b1c9fc7f99))

## v3.10.0 (2021-05-04)
### Feature
* Improve lights controls and support colors ([#1270](https://github.com/custom-components/alexa_media_player/issues/1270)) ([`fe48034`](https://github.com/custom-components/alexa_media_player/commit/fe480342498556cbf1e42ed965c69993940aea7d))
* Add "alexa_media_alarm_dismissal_event" "status"/"dismissed" events to alarms. ([#1271](https://github.com/custom-components/alexa_media_player/issues/1271)) ([`32e802f`](https://github.com/custom-components/alexa_media_player/commit/32e802f0552f4f05f039b8a3c11555e9a2dcd227))
* Add PT-BR localization ([#1266](https://github.com/custom-components/alexa_media_player/issues/1266)) ([`6a365ad`](https://github.com/custom-components/alexa_media_player/commit/6a365adaa69c3a00297164c3c8dfc79161ea67e4))

### Fix
* Fix tesla_custom compatibility ([`dada99f`](https://github.com/custom-components/alexa_media_player/commit/dada99f83461c0b189ff098a9b2e010d772f4867))
* Add iot_class to manifest.json ([`b7a3688`](https://github.com/custom-components/alexa_media_player/commit/b7a36887a0e25849c2b2f3824abd8b86344d9b77))

### Documentation
* Update localization ([`9394e97`](https://github.com/custom-components/alexa_media_player/commit/9394e9750075e4f5c665030dd4f86074bc085cbb))

## v3.9.0 (2021-04-24)
### Feature
* Add lights and the temperature sensors ([#1244](https://github.com/custom-components/alexa_media_player/issues/1244)) ([`26b4b51`](https://github.com/custom-components/alexa_media_player/commit/26b4b51b26899636b2b3ae8ac2f58b1fc2e6b433))

### Fix
* Detect and ignore lights created by emulated_hue ([#1253](https://github.com/custom-components/alexa_media_player/issues/1253)) ([`4cef90e`](https://github.com/custom-components/alexa_media_player/commit/4cef90ef73c1adcdf8e870654abc25cb2e0326e0))
* Auto reload when extended entity discovery is enabled ([#1254](https://github.com/custom-components/alexa_media_player/issues/1254)) ([`8a8f8ee`](https://github.com/custom-components/alexa_media_player/commit/8a8f8ee0e54fd4d09e3f7fc4ab2e114bbee9e2f0))
* TypeError: _typeddict_new() missing typename ([`b89852d`](https://github.com/custom-components/alexa_media_player/commit/b89852d2e50bb9c04dc5d7a70721c7073f647b3b))
* Check for existence of properties key ([`211015f`](https://github.com/custom-components/alexa_media_player/commit/211015fc16731ac496f0b4365499cf2b77928c22))

## v3.8.6 (2021-04-12)
### Fix
* Check for hass existence and fallback call ([`f2d8362`](https://github.com/custom-components/alexa_media_player/commit/f2d83625dd90c8d431ce0169714275c6d2cee836))

## v3.8.5 (2021-03-17)
### Fix
* Fix case where proxy receives ip address only ([`2c423a4`](https://github.com/custom-components/alexa_media_player/commit/2c423a4d8752450fe95d7893b86a3207b962944e))
* Use ha converter for local time ([`6c03b9c`](https://github.com/custom-components/alexa_media_player/commit/6c03b9c0ee13a813d99422f2fc800513155d88f5))

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
