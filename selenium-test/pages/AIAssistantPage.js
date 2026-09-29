const {
    By,
    Key
} = require("selenium-webdriver");


class AIAssistantPage {

    constructor(driver) {

        this.driver = driver;


        // ==================================================
        // 顶部 AI助手 导航
        // ==================================================

        this.aiNav =
            By.xpath(
                '//*[normalize-space(.)="AI助手"]'
            );


        // ==================================================
        // AI 助手面板标题
        // ==================================================

        this.panelTitle =
            By.xpath(
                '//*[normalize-space(.)="知航AI助手"]'
            );


        // ==================================================
        // AI 助手副标题
        // ==================================================

        this.panelSubtitle =
            By.xpath(
                '//*[contains(normalize-space(.), "你的学习与工作智能伙伴")]'
            );


        // ==================================================
        // 三个功能标签
        // ==================================================

        this.chatTab =
            By.xpath(
                '//*[normalize-space(.)="对话"]'
            );


        this.recommendTab =
            By.xpath(
                '//*[normalize-space(.)="推荐"]'
            );


        this.writeTab =
            By.xpath(
                '//*[normalize-space(.)="写作"]'
            );


        // ==================================================
        // AI 输入框
        //
        // 同时兼容：
        // textarea
        // input
        // contenteditable
        // ==================================================

        this.input =
            By.css(
                [
                    'textarea[placeholder*="描述你的需求"]',
                    'input[placeholder*="描述你的需求"]',
                    '[contenteditable="true"]'
                ].join(",")
            );

    }


    // ==================================================
    // 判断 locator 是否存在可见元素
    // ==================================================

    async isLocatorVisible(locator) {

        const elements =
            await this.driver.findElements(
                locator
            );


        for (const element of elements) {

            try {

                if (
                    await element.isDisplayed()
                ) {

                    return true;
                }

            } catch (error) {

                // Vue 更新过程中元素可能失效
            }

        }


        return false;

    }


    // ==================================================
    // 获取真正可见的元素
    // ==================================================

    async getVisibleElement(
        locator,
        timeout = 15000
    ) {

        return await this.driver.wait(

            async () => {

                const elements =
                    await this.driver.findElements(
                        locator
                    );


                for (const element of elements) {

                    try {

                        if (
                            await element.isDisplayed()
                        ) {

                            return element;
                        }

                    } catch (error) {

                        // 继续寻找
                    }

                }


                return false;

            },

            timeout,

            "没有找到可见元素"

        );

    }


    // ==================================================
    // 判断问卷遮罩是否显示
    // ==================================================

    async isQuestionnaireOverlayVisible() {

        const overlays =
            await this.driver.findElements(
                By.css(
                    ".questionnaire-overlay"
                )
            );


        for (const overlay of overlays) {

            try {

                if (
                    await overlay.isDisplayed()
                ) {

                    return true;
                }

            } catch (error) {

                // 忽略
            }

        }


        return false;

    }


    // ==================================================
    // 自动关闭问卷遮罩
    // ==================================================

    async closeQuestionnaireOverlay() {

        const visible =
            await this
                .isQuestionnaireOverlayVisible();


        if (!visible) {

            return;
        }


        console.log(
            "\n检测到问卷遮罩层，尝试关闭..."
        );


        const overlays =
            await this.driver.findElements(
                By.css(
                    ".questionnaire-overlay"
                )
            );


        for (const overlay of overlays) {

            try {

                if (
                    !await overlay.isDisplayed()
                ) {

                    continue;
                }


                // ==========================================
                // 方法 1
                // 查找关闭 / 跳过 / 稍后等按钮
                // ==========================================

                const buttons =
                    await overlay.findElements(
                        By.xpath(
                            './/button[' +
                            'contains(normalize-space(.), "关闭") or ' +
                            'contains(normalize-space(.), "跳过") or ' +
                            'contains(normalize-space(.), "稍后") or ' +
                            'contains(normalize-space(.), "取消") or ' +
                            '@aria-label="关闭" or ' +
                            '@aria-label="Close"' +
                            ']'
                        )
                    );


                for (const button of buttons) {

                    try {

                        if (
                            await button.isDisplayed()
                        ) {

                            await button.click();


                            await this.driver.sleep(
                                300
                            );


                            console.log(
                                "问卷遮罩层已通过按钮关闭"
                            );


                            return;
                        }

                    } catch (error) {

                        // 继续
                    }

                }


                // ==========================================
                // 方法 2
                // ESC
                // ==========================================

                try {

                    await this.driver
                        .actions()
                        .sendKeys(
                            Key.ESCAPE
                        )
                        .perform();


                    await this.driver.sleep(
                        300
                    );


                    if (
                        !await this
                            .isQuestionnaireOverlayVisible()
                    ) {

                        console.log(
                            "问卷遮罩层已通过 Escape 关闭"
                        );


                        return;
                    }

                } catch (error) {

                    // 继续
                }


                // ==========================================
                // 方法 3
                // 自动化测试环境兜底隐藏
                // ==========================================

                await this.driver.executeScript(
                    `
                    document
                        .querySelectorAll(
                            ".questionnaire-overlay"
                        )
                        .forEach(
                            element => {
                                element.style.display =
                                    "none";
                            }
                        );
                    `
                );


                console.log(
                    "问卷遮罩层已临时隐藏"
                );


                return;

            } catch (error) {

                // 忽略
            }

        }

    }


    // ==================================================
    // 判断 AI 助手是否展开
    // ==================================================

    async isOpen() {

        const titleVisible =
            await this.isLocatorVisible(
                this.panelTitle
            );


        const inputVisible =
            await this.isLocatorVisible(
                this.input
            );


        return (
            titleVisible &&
            inputVisible
        );

    }


    // ==================================================
    // 点击顶部 AI助手
    // ==================================================

    async clickAINav() {

        await this
            .closeQuestionnaireOverlay();


        const elements =
            await this.driver.findElements(
                this.aiNav
            );


        let target =
            null;


        for (const element of elements) {

            try {

                if (
                    !await element.isDisplayed()
                ) {

                    continue;
                }


                target =
                    await this.driver
                        .executeScript(
                            `
                            const element =
                                arguments[0];


                            return (
                                element.closest(
                                    "button, a, [role='button']"
                                )
                                ||
                                element
                            );
                            `,
                            element
                        );


                if (target) {

                    break;
                }

            } catch (error) {

                // 继续
            }

        }


        if (!target) {

            throw new Error(
                "没有找到顶部 AI助手 按钮"
            );

        }


        try {

            await target.click();

        } catch (error) {

            console.log(
                "\n普通点击 AI助手 失败，使用 JS click..."
            );


            await this.driver.executeScript(
                `
                arguments[0].click();
                `,
                target
            );

        }


        await this.driver.sleep(
            500
        );

    }


    // ==================================================
    // 展开 AI 助手
    // ==================================================

    async open() {

        if (
            await this.isOpen()
        ) {

            return;
        }


        await this.clickAINav();


        await this.driver.wait(

            async () => {

                return await this.isOpen();

            },

            15000,

            "点击 AI助手 后，AI 面板没有展开"

        );


        console.log(
            "\nAI助手已成功展开"
        );

    }


    // ==================================================
    // 获取 AI 助手面板本体
    // ==================================================

    async getPanel() {

        const title =
            await this.getVisibleElement(
                this.panelTitle
            );


        const panel =
            await this.driver.executeScript(
                `
                const title =
                    arguments[0];


                let node =
                    title;


                while (
                    node &&
                    node !== document.body
                ) {

                    const rect =
                        node.getBoundingClientRect();


                    // 面板位于右侧，
                    // 且尺寸明显大于普通按钮
                    if (
                        rect.width > 250
                        &&
                        rect.height > 300
                        &&
                        rect.right >
                            window.innerWidth * 0.8
                    ) {

                        return node;
                    }


                    node =
                        node.parentElement;
                }


                return null;
                `,
                title
            );


        if (!panel) {

            throw new Error(
                "没有找到 AI 助手面板"
            );

        }


        return panel;

    }


    // ==================================================
    // 点击右上角 X 关闭 AI 助手
    // ==================================================

    async closeByX() {

        if (
            !await this.isOpen()
        ) {

            return;
        }


        const panel =
            await this.getPanel();


        const closeButton =
            await this.driver.executeScript(
                `
                const panel =
                    arguments[0];


                const buttons =
                    Array.from(
                        panel.querySelectorAll(
                            "button, [role='button']"
                        )
                    );


                const panelRect =
                    panel.getBoundingClientRect();


                let best =
                    null;


                let bestScore =
                    -99999;


                for (
                    const button
                    of buttons
                ) {

                    const rect =
                        button.getBoundingClientRect();


                    if (
                        rect.width <= 0
                        ||
                        rect.height <= 0
                    ) {

                        continue;
                    }


                    const text =
                        (
                            button.innerText ||
                            button.textContent ||
                            ""
                        ).trim();


                    const aria =
                        (
                            button.getAttribute(
                                "aria-label"
                            ) || ""
                        );


                    const title =
                        (
                            button.getAttribute(
                                "title"
                            ) || ""
                        );


                    const value =
                        (
                            text +
                            " " +
                            aria +
                            " " +
                            title
                        ).toLowerCase();


                    let score =
                        0;


                    // ======================================
                    // 明确关闭语义
                    // ======================================

                    if (
                        value.includes(
                            "关闭"
                        )
                        ||
                        value.includes(
                            "close"
                        )
                        ||
                        text === "×"
                        ||
                        text === "✕"
                    ) {

                        score += 500;
                    }


                    // ======================================
                    // 位于面板右上角
                    // ======================================

                    const centerX =
                        rect.left +
                        rect.width / 2;


                    const centerY =
                        rect.top +
                        rect.height / 2;


                    if (
                        centerX >
                            panelRect.right - 100
                        &&
                        centerY <
                            panelRect.top + 100
                    ) {

                        score += 150;
                    }


                    // ======================================
                    // 排除最小化按钮
                    // ======================================

                    if (
                        text === "-"
                        ||
                        text === "−"
                    ) {

                        score -= 500;
                    }


                    if (
                        score >
                        bestScore
                    ) {

                        bestScore =
                            score;


                        best =
                            button;
                    }

                }


                if (
                    !best ||
                    bestScore < 100
                ) {

                    return null;
                }


                return best;
                `,
                panel
            );


        if (!closeButton) {

            throw new Error(
                "没有找到 AI 助手右上角关闭按钮"
            );

        }


        try {

            await closeButton.click();

        } catch (error) {

            await this.driver.executeScript(
                `
                arguments[0].click();
                `,
                closeButton
            );

        }


        await this.driver.wait(

            async () => {

                return !await this.isOpen();

            },

            10000,

            "点击关闭按钮后 AI 助手仍然显示"

        );


        console.log(
            "AI助手已成功关闭"
        );

    }


    // ==================================================
    // 判断“对话”是否显示
    // ==================================================

    async isChatTabVisible() {

        return await this.isLocatorVisible(
            this.chatTab
        );

    }


    // ==================================================
    // 判断“推荐”是否显示
    // ==================================================

    async isRecommendTabVisible() {

        return await this.isLocatorVisible(
            this.recommendTab
        );

    }


    // ==================================================
    // 判断“写作”是否显示
    // ==================================================

    async isWriteTabVisible() {

        return await this.isLocatorVisible(
            this.writeTab
        );

    }


    // ==================================================
    // 输入框是否显示
    // ==================================================

    async isInputVisible() {

        return await this.isLocatorVisible(
            this.input
        );

    }


    // ==================================================
    // 输入测试文字
    //
    // 不点击发送
    // 不调用真实 AI
    // ==================================================

    async typeMessage(message) {

        const input =
            await this.getVisibleElement(
                this.input
            );


        // ==========================================
        // 滚动到输入框
        // ==========================================

        await this.driver.executeScript(
            `
            arguments[0].scrollIntoView({
                block: "center",
                inline: "center"
            });
            `,
            input
        );


        // ==========================================
        // 点击输入框
        // ==========================================

        try {

            await input.click();

        } catch (error) {

            await this.driver.executeScript(
                `
                arguments[0].focus();
                `,
                input
            );

        }


        // ==========================================
        // 获取元素类型
        // ==========================================

        const elementInfo =
            await this.driver.executeScript(
                `
                const element =
                    arguments[0];


                return {
                    tagName:
                        element.tagName
                            .toLowerCase(),

                    contentEditable:
                        element.isContentEditable,

                    value:
                        element.value !== undefined
                            ? element.value
                            : null
                };
                `,
                input
            );


        // ==========================================
        // 普通 textarea / input
        // ==========================================

        if (
            elementInfo.tagName ===
                "textarea"
            ||
            elementInfo.tagName ===
                "input"
        ) {

            // Ctrl + A
            await input.sendKeys(
                Key.chord(
                    Key.CONTROL,
                    "a"
                )
            );


            // 删除旧内容
            await input.sendKeys(
                Key.BACK_SPACE
            );


            // 输入测试内容
            await input.sendKeys(
                message
            );

        }


        // ==========================================
        // contenteditable
        // ==========================================

        else if (
            elementInfo.contentEditable
        ) {

            await input.sendKeys(
                Key.chord(
                    Key.CONTROL,
                    "a"
                )
            );


            await input.sendKeys(
                Key.BACK_SPACE
            );


            await input.sendKeys(
                message
            );

        }


        // ==========================================
        // 最后兜底
        // ==========================================

        else {

            await this.driver.executeScript(
                `
                const element =
                    arguments[0];

                const text =
                    arguments[1];


                element.focus();


                if (
                    "value" in element
                ) {

                    element.value =
                        text;


                    element.dispatchEvent(
                        new Event(
                            "input",
                            {
                                bubbles: true
                            }
                        )
                    );


                    element.dispatchEvent(
                        new Event(
                            "change",
                            {
                                bubbles: true
                            }
                        )
                    );

                } else {

                    element.textContent =
                        text;


                    element.dispatchEvent(
                        new InputEvent(
                            "input",
                            {
                                bubbles: true,
                                inputType:
                                    "insertText",
                                data:
                                    text
                            }
                        )
                    );

                }
                `,
                input,
                message
            );

        }


        // ==========================================
        // 等 Vue v-model 更新
        // ==========================================

        await this.driver.sleep(
            500
        );


        // ==========================================
        // 获取真实输入内容
        // ==========================================

        const currentValue =
            await this.driver.executeScript(
                `
                const element =
                    arguments[0];


                if (
                    element.value !== undefined
                    &&
                    element.value !== null
                ) {

                    return element.value;
                }


                if (
                    element.isContentEditable
                ) {

                    return (
                        element.innerText ||
                        element.textContent ||
                        ""
                    );
                }


                return (
                    element.innerText ||
                    element.textContent ||
                    ""
                );
                `,
                input
            );


        console.log(
            "\nAI输入框当前内容：",
            currentValue
        );


        return currentValue;

    }


    // ==================================================
    // 获取输入框中的真实实时内容
    // ==================================================

    async getInputValue() {

        const input =
            await this.getVisibleElement(
                this.input
            );


        const value =
            await this.driver.executeScript(
                `
                const element =
                    arguments[0];


                // ======================================
                // textarea / input
                // ======================================

                if (
                    element.value !== undefined
                    &&
                    element.value !== null
                ) {

                    return element.value;
                }


                // ======================================
                // contenteditable
                // ======================================

                if (
                    element.isContentEditable
                ) {

                    return (
                        element.innerText ||
                        element.textContent ||
                        ""
                    );
                }


                // ======================================
                // 普通文本节点兜底
                // ======================================

                return (
                    element.innerText ||
                    element.textContent ||
                    ""
                );
                `,
                input
            );


        const result =
            (
                value || ""
            ).trim();


        console.log(
            "读取到的AI输入框内容：",
            result
        );


        return result;

    }

}


module.exports = AIAssistantPage;