# Fluent resource for IronForge RPG Act 3
# namespace: ironforge-rpg
# clan: game
# source-language: zh-CN
# target-language: en-US
# title: IronForge RPG - Act 3 dialog
# info: The mountain city of IronForge, one week after the siege.
# info: Anvil is a warm, plain-spoken dwarf blacksmith; Captain Mei is formal in public, warm to friends. The player returns to the blacksmith to reclaim a repaired sword.
# standard: Preserve proper nouns; localize idioms for humor.
# standard: Keep UI labels under the declared max-width.
# dependency: ../terms/ironforge.terms.en-US.cliff
# dependency: docs/act3-script.md

-term-iron-sword = Iron Sword
    .source = 铁剑
    .type = noun
    .status = final
    .context = Canonical game term.
-term-traveler = traveler
    .source = 旅行者
    .type = noun
    .status = final
    .context = Canonical game term.
-term-forge = forge
    .source = 铁匠铺
    .type = noun
    .status = final
    .context = Canonical game term.

items-shop-inv-sword-iron = Iron Sword
    .id = inv-sword-iron
    .source = 铁剑
    .group = items.shop
    .type = noun
    .emotion = playful
    .status = final
    .context = Blacksmith shop, purchase confirmation popup.
    .max-width = 20
    .reference = src/combat/items.cpp:142

items-shop-inv-potion-heal = Healing Potion
    .id = inv-potion-heal
    .source = 恢复药水
    .group = items.shop
    .type = noun-phrase
    .emotion = playful
    .status = translated
    .context = Blacksmith shop, purchase confirmation popup.
    .max-width = 20

items-shop-inv-armor-mithril = Mithril Armor
    .id = inv-armor-mithril
    .source = 秘银护甲
    .group = items.shop
    .type = noun-phrase
    .emotion = playful
    .status = reviewed
    .context = Blacksmith shop, purchase confirmation popup.
    .max-width = 20

items-shop-inv-axe-rune = Rune Battleaxe
    .id = inv-axe-rune
    .source = 符文战斧
    .group = items.shop
    .type = noun
    .emotion = playful
    .status = final
    .context = Blacksmith shop, purchase confirmation popup.
    .max-width = 20

dialog-act3-first-meet-greeting = Hello, traveler.
    .id = greeting
    .source = 你好，旅行者。
    .group = dialog.act3.first-meet
    .type = dialogue
    .emotion = polite calm
    .status = final
    .context = The player meets Captain Mei at the city gate after the siege.

dialog-act3-first-meet-ask-origin = Where do you come from?
    .id = ask-origin
    .source = 你从哪里来？
    .group = dialog.act3.first-meet
    .type = dialogue
    .emotion = polite curious
    .status = reviewed
    .context = The player meets Captain Mei at the city gate after the siege.

dialog-act3-first-meet-ask-companion = {name}, is {gender, select, male {he} female {she} other {they}} your companion?
    .id = ask-companion
    .source = {name}，{gender, select, male {他} female {她} other {他们}} 是你的同伴吗？
    .group = dialog.act3.first-meet
    .type = sentence
    .emotion = surprised playful
    .status = reviewed
    .context = The player meets Captain Mei at the city gate after the siege. She points at the silent stranger next to the player.
    .reference = src/dialog/act3.cpp:87

dialog-act3-first-meet-ask-city = Is the city still safe?
    .id = ask-city
    .source = 城里还安全吗？
    .group = dialog.act3.first-meet
    .type = dialogue
    .emotion = neutral
    .status = reviewed
    .context = The player meets Captain Mei at the city gate after the siege.

dialog-act3-first-meet-ask-sword = Was your sword newly forged?
    .id = ask-sword
    .source = 你的剑是新打的吗？
    .group = dialog.act3.first-meet
    .type = dialogue
    .emotion = neutral
    .status = reviewed
    .context = The player meets Captain Mei at the city gate after the siege.

dialog-act3-farewell-farewell = Safe travels, traveler!
    .id = farewell
    .source = 一路顺风，旅行者！
    .group = dialog.act3.farewell
    .type = dialogue
    .emotion = playful joyful
    .status = reviewed
    .context = The player leaves the forge with the repaired sword.

dialog-act3-farewell-farewell-pun = A swordsman without a sword is a fish out of water - let's have a re-"blade" meeting soon!
    .id = farewell-pun
    .source = 剑客无剑，如鱼无水——改天我请你“剑”面！
    .group = dialog.act3.farewell
    .type = dialogue
    .emotion = playful joyful
    .status = reviewed
    .context = The player leaves the forge with the repaired sword. Anvil winks; the pun is on 见/剑.

dialog-act3-farewell-come-again = Come back anytime!
    .id = come-again
    .source = 下次再来！
    .group = dialog.act3.farewell
    .type = dialogue
    .emotion = playful joyful
    .status = final
    .context = The player leaves the forge with the repaired sword.

quests-reward-reward-title = The Blacksmith's Gratitude
    .id = reward-title
    .source = 铁匠的谢礼
    .group = quests.reward
    .type = label
    .emotion = grateful
    .status = final
    .context = Quest reward screen after the sword is returned.

quests-reward-reward-body = Please take this charm.
    .id = reward-body
    .source = 收下这枚护符吧。
    .group = quests.reward
    .type = narration
    .emotion = grateful
    .status = reviewed
    .context = Quest reward screen after the sword is returned.

quests-reward-reward-count = {count, plural, =0 {No rewards} one {# reward} other {# rewards}}
    .id = reward-count
    .source = {count, plural, =0 {没有奖励} one {# 件奖励} other {# 件奖励}}
    .group = quests.reward
    .type = sentence
    .emotion = grateful
    .status = reviewed
    .context = Quest reward screen after the sword is returned.

quests-reward-reward-accept = Accept
    .id = reward-accept
    .source = 接受
    .group = quests.reward
    .type = label
    .emotion = grateful
    .status = final
    .context = Quest reward screen after the sword is returned.
    .max-width = 8

