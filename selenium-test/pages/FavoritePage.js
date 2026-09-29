const {
    By,
    Key
} = require("selenium-webdriver");


class FavoritePage {

    constructor(driver) {

        this.driver = driver;

        this.baseUrl =
            "http://127.0.0.1:5173";

        this.url =
            `${this.baseUrl}/favorites`;


        // 顶部收藏导航
        this.favoriteNav =
            By.css(
                'a[href="/favorites"], a[href$="/favorites"]'
            );


        // 有收藏内容时的标题
        this.pageTitle =
            By.xpath(
                '//*[normalize-space(.)="收藏资源"]'
            );


        // 收藏夹为空时的真实页面文字
        this.emptyStateTitle =
            By.xpath(
                '//*[normalize-space(.)="收藏夹还是空的"]'
            );

    }


    // ==================================================
    // 判断元素是否可见
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
                // Vue 更新期间元素可能失效
            }

        }


        return false;

    }


    // ==================================================
    // 获取一个真正可见的元素
    // ==================================================

    async getVisibleElement(
        locator,
        timeout = 20000
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
    // 判断问卷遮罩
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
    // 等待遮罩消失
    // ==================================================

    async waitForOverlayToDisappear(
        timeout = 5000
    ) {

        try {

            await this.driver.wait(

                async () => {

                    return !await this
                        .isQuestionnaireOverlayVisible();

                },

                timeout

            );

        } catch (error) {
            // 后面还有兜底
        }

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


                // ------------------------------------------
                // 第一种：正常关闭按钮
                // ------------------------------------------

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


                            await this
                                .waitForOverlayToDisappear();


                            console.log(
                                "问卷遮罩层已通过按钮关闭"
                            );


                            return;
                        }

                    } catch (error) {
                        // 继续
                    }

                }


                // ------------------------------------------
                // 第二种：ESC
                // ------------------------------------------

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


                // ------------------------------------------
                // 第三种：测试环境隐藏
                // ------------------------------------------

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
                    "问卷遮罩层已在测试环境中临时隐藏"
                );


                return;

            } catch (error) {
                // 忽略
            }

        }

    }


    // ==================================================
    // 打开收藏页面
    // ==================================================

    async open() {

        const currentUrl =
            await this.driver
                .getCurrentUrl();


        // 已经在收藏页面
        if (
            currentUrl.includes(
                "/favorites"
            )
        ) {

            await this.waitForLoaded();

            await this
                .closeQuestionnaireOverlay();

            return;
        }


        await this
            .closeQuestionnaireOverlay();


        let favoriteButton =
            null;


        // ------------------------------------------
        // 优先使用 href
        // ------------------------------------------

        const links =
            await this.driver.findElements(
                this.favoriteNav
            );


        for (const link of links) {

            try {

                if (
                    await link.isDisplayed()
                ) {

                    favoriteButton =
                        link;

                    break;
                }

            } catch (error) {
                // 继续
            }

        }


        // ------------------------------------------
        // 文字定位兜底
        // ------------------------------------------

        if (!favoriteButton) {

            const candidates =
                await this.driver.findElements(
                    By.xpath(
                        '//*[normalize-space(.)="收藏"]'
                    )
                );


            for (const element of candidates) {

                try {

                    if (
                        !await element.isDisplayed()
                    ) {

                        continue;
                    }


                    favoriteButton =
                        await this.driver
                            .executeScript(
                                `
                                const element =
                                    arguments[0];

                                return (
                                    element.closest(
                                        'a[href="/favorites"]'
                                    )
                                    ||
                                    element.closest(
                                        'a[href$="/favorites"]'
                                    )
                                    ||
                                    element.closest(
                                        "a, button, [role='button']"
                                    )
                                    ||
                                    element
                                );
                                `,
                                element
                            );


                    if (favoriteButton) {

                        break;
                    }

                } catch (error) {
                    // 继续
                }

            }

        }


        if (!favoriteButton) {

            throw new Error(
                "没有找到顶部收藏导航"
            );
        }


        await this.driver.executeScript(
            `
            arguments[0].scrollIntoView({
                block: "center",
                inline: "center"
            });
            `,
            favoriteButton
        );


        await this.driver.sleep(
            200
        );


        await this
            .closeQuestionnaireOverlay();


        try {

            await favoriteButton.click();

        } catch (error) {

            console.log(
                "\n普通点击收藏导航失败，使用 JS click..."
            );


            await this.driver.executeScript(
                `
                arguments[0].click();
                `,
                favoriteButton
            );

        }


        await this.driver.wait(

            async () => {

                const url =
                    await this.driver
                        .getCurrentUrl();


                return url.includes(
                    "/favorites"
                );

            },

            20000,

            "点击收藏导航后没有进入 /favorites 页面"

        );


        console.log(
            "\n已进入收藏页：",
            await this.driver.getCurrentUrl()
        );


        await this.waitForLoaded();


        await this
            .closeQuestionnaireOverlay();

    }


    // ==================================================
    // 判断收藏页是否真正加载
    // ==================================================

    async isPageLoaded() {

        const url =
            await this.driver
                .getCurrentUrl();


        if (
            !url.includes(
                "/favorites"
            )
        ) {

            return false;
        }


        // 空收藏夹
        if (
            await this.isLocatorVisible(
                this.emptyStateTitle
            )
        ) {

            return true;
        }


        // 有收藏时的标题
        if (
            await this.isLocatorVisible(
                this.pageTitle
            )
        ) {

            return true;
        }


        // 收藏卡片
        if (
            await this.isLocatorVisible(
                By.css(
                    ".site-card"
                )
            )
        ) {

            return true;
        }


        return false;

    }


    // ==================================================
    // 等待收藏页加载
    // ==================================================

    async waitForLoaded() {

        await this.driver.wait(

            async () => {

                const url =
                    await this.driver
                        .getCurrentUrl();


                return url.includes(
                    "/favorites"
                );

            },

            20000,

            "没有进入 /favorites 页面"

        );


        await this.driver.wait(

            async () => {

                return await this
                    .isPageLoaded();

            },

            20000,

            "收藏页面没有正常加载"

        );


        if (
            await this.isEmptyStateVisible()
        ) {

            console.log(
                "\n收藏页面加载成功：当前收藏夹为空"
            );

        } else {

            console.log(
                "\n收藏页面加载成功：存在收藏内容"
            );

        }

    }


    // ==================================================
    // 空收藏状态
    // ==================================================

    async isEmptyStateVisible() {

        return await this.isLocatorVisible(
            this.emptyStateTitle
        );

    }


    // ==================================================
    // 页面标题
    // ==================================================

    async isPageTitleVisible() {

        return await this.isLocatorVisible(
            this.pageTitle
        );

    }


    // ==================================================
    // 资源是否存在
    // ==================================================

    async isResourceVisible(
        resourceName
    ) {

        return await this.isLocatorVisible(

            By.xpath(
                `//*[normalize-space(.)="${resourceName}"]`
            )

        );

    }


    // ==================================================
    // 等待资源出现 / 消失
    // ==================================================

    async waitForResourceState(
        resourceName,
        shouldExist,
        timeout = 15000
    ) {

        await this.driver.wait(

            async () => {

                const visible =
                    await this
                        .isResourceVisible(
                            resourceName
                        );


                return (
                    visible === shouldExist
                );

            },

            timeout,

            shouldExist
                ?
                `${resourceName} 没有出现在收藏页`
                :
                `${resourceName} 没有从收藏页消失`

        );

    }


    // ==================================================
    // 获取完整资源卡片
    // ==================================================

    async getResourceCard(
        resourceName
    ) {

        const title =
            await this.getVisibleElement(

                By.xpath(
                    `//*[normalize-space(.)="${resourceName}"]`
                ),

                15000

            );


        const card =
            await this.driver.executeScript(
                `
                const title =
                    arguments[0];


                const directCard =
                    title.closest(
                        ".site-card"
                    );


                if (directCard) {

                    return directCard;
                }


                let node =
                    title;


                while (
                    node &&
                    node !== document.body
                ) {

                    if (
                        node.classList &&
                        node.classList.contains(
                            "site-card"
                        )
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


        if (!card) {

            throw new Error(
                `没有找到 ${resourceName} 的完整资源卡片`
            );
        }


        return card;

    }


    // ==================================================
    // 智能寻找收藏星标
    //
    // 同时考虑：
    // 语义、class、位置
    // ==================================================

    async getFavoriteButtonForResource(
        resourceName
    ) {

        const card =
            await this.getResourceCard(
                resourceName
            );


        const button =
            await this.driver.executeScript(
                `
                const card =
                    arguments[0];


                const cardRect =
                    card.getBoundingClientRect();


                const candidates =
                    Array.from(
                        card.querySelectorAll(
                            [
                                "button",
                                "[role='button']",
                                "[aria-label]",
                                "[title]",
                                "[class*='favorite']",
                                "[class*='Favorite']",
                                "[class*='star']",
                                "[class*='Star']",
                                "[class*='bookmark']",
                                "[class*='Bookmark']",
                                "svg"
                            ].join(",")
                        )
                    );


                let best =
                    null;


                let bestScore =
                    -999999;


                for (
                    const element
                    of candidates
                ) {

                    const rect =
                        element
                            .getBoundingClientRect();


                    if (
                        rect.width <= 0
                        ||
                        rect.height <= 0
                    ) {

                        continue;
                    }


                    const aria =
                        (
                            element.getAttribute(
                                "aria-label"
                            ) || ""
                        );


                    const title =
                        (
                            element.getAttribute(
                                "title"
                            ) || ""
                        );


                    const text =
                        (
                            element.innerText ||
                            element.textContent ||
                            ""
                        ).trim();


                    const className =
                        (
                            element.getAttribute(
                                "class"
                            ) || ""
                        );


                    const value =
                        (
                            aria +
                            " " +
                            title +
                            " " +
                            text +
                            " " +
                            className
                        ).toLowerCase();


                    let score =
                        0;


                    // ------------------------------
                    // 明确收藏语义
                    // ------------------------------

                    if (
                        value.includes(
                            "取消收藏"
                        )
                    ) {

                        score += 500;
                    }


                    if (
                        value.includes(
                            "收藏"
                        )
                    ) {

                        score += 300;
                    }


                    if (
                        value.includes(
                            "favorite"
                        )
                        ||
                        value.includes(
                            "favourite"
                        )
                    ) {

                        score += 250;
                    }


                    if (
                        value.includes(
                            "star"
                        )
                    ) {

                        score += 200;
                    }


                    if (
                        value.includes(
                            "bookmark"
                        )
                    ) {

                        score += 200;
                    }


                    // ------------------------------
                    // 排除明显不是收藏的按钮
                    // ------------------------------

                    if (
                        value.includes(
                            "访问"
                        )
                        ||
                        value.includes(
                            "查看详情"
                        )
                        ||
                        value.includes(
                            "python 文档"
                        )
                    ) {

                        score -= 300;
                    }


                    // ------------------------------
                    // 收藏星星位于卡片右上角
                    // ------------------------------

                    const centerX =
                        rect.left +
                        rect.width / 2;


                    const centerY =
                        rect.top +
                        rect.height / 2;


                    const rightArea =
                        centerX >
                        (
                            cardRect.left +
                            cardRect.width * 0.68
                        );


                    const topArea =
                        centerY <
                        (
                            cardRect.top +
                            cardRect.height * 0.35
                        );


                    if (
                        rightArea &&
                        topArea
                    ) {

                        score += 180;
                    }


                    // ------------------------------
                    // 小图标更可能是星标
                    // ------------------------------

                    if (
                        rect.width <= 80
                        &&
                        rect.height <= 80
                    ) {

                        score += 30;
                    }


                    if (
                        score >
                        bestScore
                    ) {

                        bestScore =
                            score;


                        best =
                            element;
                    }

                }


                if (
                    !best ||
                    bestScore < 50
                ) {

                    return null;
                }


                return (
                    best.closest(
                        "button, [role='button'], a"
                    )
                    ||
                    best
                );
                `,
                card
            );


        return button;

    }


    // ==================================================
    // 点击卡片右上角的星标
    //
    // 这是专门的几何定位兜底
    // ==================================================

    async clickTopRightFavoriteControl(
        resourceName
    ) {

        const card =
            await this.getResourceCard(
                resourceName
            );


        const result =
            await this.driver.executeScript(
                `
                const card =
                    arguments[0];


                const rect =
                    card.getBoundingClientRect();


                // 根据真实页面截图：
                // 星星位于卡片右上角
                const points = [

                    {
                        x:
                            rect.right - 42,

                        y:
                            rect.top + 42
                    },

                    {
                        x:
                            rect.right - 35,

                        y:
                            rect.top + 35
                    },

                    {
                        x:
                            rect.right - 50,

                        y:
                            rect.top + 50
                    },

                    {
                        x:
                            rect.right - 32,

                        y:
                            rect.top + 45
                    }

                ];


                for (const point of points) {

                    const element =
                        document.elementFromPoint(
                            point.x,
                            point.y
                        );


                    if (!element) {

                        continue;
                    }


                    if (
                        !card.contains(
                            element
                        )
                    ) {

                        continue;
                    }


                    const target =
                        element.closest(
                            "button, [role='button'], a"
                        )
                        ||
                        element;


                    if (
                        typeof target.click
                        === "function"
                    ) {

                        target.click();


                        return {

                            clicked:
                                true,

                            tag:
                                target.tagName,

                            className:
                                target.getAttribute(
                                    "class"
                                ),

                            ariaLabel:
                                target.getAttribute(
                                    "aria-label"
                                ),

                            x:
                                point.x,

                            y:
                                point.y

                        };
                    }


                    target.dispatchEvent(
                        new MouseEvent(
                            "click",
                            {
                                bubbles: true,
                                cancelable: true,
                                view: window
                            }
                        )
                    );


                    return {

                        clicked:
                            true,

                        tag:
                            target.tagName,

                        className:
                            target.getAttribute(
                                "class"
                            ),

                        ariaLabel:
                            target.getAttribute(
                                "aria-label"
                            ),

                        x:
                            point.x,

                        y:
                            point.y

                    };

                }


                return {

                    clicked:
                        false

                };
                `,
                card
            );


        console.log(
            "\n右上角星标点击结果：",
            result
        );


        return (
            result &&
            result.clicked === true
        );

    }


    // ==================================================
    // 通用收藏点击
    //
    // 主要用于搜索结果页进行“收藏”
    // ==================================================

    async clickFavoriteToggleForResource(
        resourceName
    ) {

        await this
            .closeQuestionnaireOverlay();


        const card =
            await this.getResourceCard(
                resourceName
            );


        let button =
            await this
                .getFavoriteButtonForResource(
                    resourceName
                );


        if (button) {

            await this.driver.executeScript(
                `
                arguments[0].scrollIntoView({
                    block: "center",
                    inline: "center"
                });
                `,
                button
            );


            await this.driver.sleep(
                200
            );


            await this
                .closeQuestionnaireOverlay();


            try {

                await button.click();

            } catch (error) {

                console.log(
                    "\n普通收藏点击失败，使用 JS click..."
                );


                await this.driver.executeScript(
                    `
                    arguments[0].click();
                    `,
                    button
                );

            }

        } else {

            console.log(
                "\n没有找到明确收藏按钮，改用右上角位置点击..."
            );


            const success =
                await this
                    .clickTopRightFavoriteControl(
                        resourceName
                    );


            if (!success) {

                throw new Error(
                    `无法点击 ${resourceName} 的收藏星标`
                );
            }

        }


        await this.driver.sleep(
            700
        );

    }


    // ==================================================
    // 专门用于收藏页取消收藏
    //
    // 比通用 toggle 更严格
    // ==================================================

    async cancelFavoriteFromFavoritesPage(
        resourceName
    ) {

        console.log(
            `\n准备取消收藏：${resourceName}`
        );


        await this
            .closeQuestionnaireOverlay();


        // ==========================================
        // 确保资源当前确实存在
        // ==========================================

        const exists =
            await this
                .isResourceVisible(
                    resourceName
                );


        if (!exists) {

            console.log(
                `${resourceName} 当前已经不在收藏页`
            );


            return true;
        }


        // ==========================================
        // 第一次：
        // 通过智能定位点击
        // ==========================================

        const button =
            await this
                .getFavoriteButtonForResource(
                    resourceName
                );


        if (button) {

            await this.driver.executeScript(
                `
                arguments[0].scrollIntoView({
                    block: "center",
                    inline: "center"
                });
                `,
                button
            );


            await this.driver.sleep(
                200
            );


            try {

                await button.click();


                console.log(
                    "已点击收藏页星标按钮"
                );

            } catch (error) {

                console.log(
                    "普通点击失败，使用 JS click..."
                );


                await this.driver.executeScript(
                    `
                    arguments[0].click();
                    `,
                    button
                );

            }

        } else {

            console.log(
                "语义定位未找到星标，直接使用右上角点击"
            );


            await this
                .clickTopRightFavoriteControl(
                    resourceName
                );

        }


        await this.driver.sleep(
            1000
        );


        // ==========================================
        // 如果页面立即移除卡片
        // 直接成功
        // ==========================================

        if (
            !await this
                .isResourceVisible(
                    resourceName
                )
        ) {

            console.log(
                `${resourceName} 已立即从收藏页消失`
            );


            return true;
        }


        // ==========================================
        // 有些 Vue 页面不会立即移除
        //
        // 刷新一次检查服务器真实状态
        // ==========================================

        console.log(
            "卡片暂未消失，刷新页面确认真实收藏状态..."
        );


        await this.driver
            .navigate()
            .refresh();


        await this.waitForLoaded();


        await this
            .closeQuestionnaireOverlay();


        if (
            !await this
                .isResourceVisible(
                    resourceName
                )
        ) {

            console.log(
                `${resourceName} 刷新后已消失，取消收藏成功`
            );


            return true;
        }


        // ==========================================
        // 刷新后仍然存在
        //
        // 说明第一次点击确实没有点中
        // 这时使用卡片右上角真实坐标点击
        // ==========================================

        console.log(
            "刷新后资源仍存在，使用卡片右上角星标精确点击..."
        );


        const coordinateClicked =
            await this
                .clickTopRightFavoriteControl(
                    resourceName
                );


        if (!coordinateClicked) {

            throw new Error(
                `无法点击 ${resourceName} 右上角收藏星标`
            );
        }


        await this.driver.sleep(
            1000
        );


        // ==========================================
        // 第二次刷新确认
        // ==========================================

        if (
            await this.isResourceVisible(
                resourceName
            )
        ) {

            await this.driver
                .navigate()
                .refresh();


            await this.waitForLoaded();


            await this
                .closeQuestionnaireOverlay();

        }


        const stillExists =
            await this
                .isResourceVisible(
                    resourceName
                );


        if (stillExists) {

            console.log(
                `${resourceName} 取消收藏后仍然存在`
            );


            return false;
        }


        console.log(
            `${resourceName} 取消收藏成功`
        );


        return true;

    }


    // ==================================================
    // 等 Toast
    // ==================================================

    async waitForMessage(
        message,
        timeout = 5000
    ) {

        return await this.getVisibleElement(

            By.xpath(
                `//*[contains(normalize-space(.), "${message}")]`
            ),

            timeout

        );

    }


    // ==================================================
    // 当前 URL
    // ==================================================

    async getCurrentUrl() {

        return await this.driver
            .getCurrentUrl();

    }

}


module.exports = FavoritePage;