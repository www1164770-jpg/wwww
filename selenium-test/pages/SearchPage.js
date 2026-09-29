const {
    By,
    Key
} = require("selenium-webdriver");


class SearchPage {

    constructor(driver) {

        this.driver = driver;


        // ==============================
        // 首页搜索框
        // ==============================

        this.searchInput =
            By.css(
                'input[placeholder*="搜索工具"]'
            );


        // ==============================
        // 搜索结果标题
        // 例如：搜索结果：Python
        // ==============================

        this.resultTitle =
            By.xpath(
                '//*[contains(normalize-space(.), "搜索结果：")]'
            );


        // ==============================
        // 搜索结果数量
        // 例如：找到 7 个相关网站
        // ==============================

        this.resultCount =
            By.xpath(
                '//*[contains(normalize-space(.), "个相关网站")]'
            );


        // ==============================
        // 搜索类型
        // ==============================

        this.searchType =
            By.xpath(
                '//*[normalize-space(.)="站内搜索"]'
            );

    }


    // ==================================================
    // 获取真正可见的元素
    // ==================================================

    async getVisibleElement(
        locator,
        timeout = 10000
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
                        // 忽略失效元素
                    }

                }


                return false;

            },

            timeout,

            "没有找到可见元素"

        );

    }


    // ==================================================
    // 搜索
    // ==================================================

    async search(keyword) {

        const input =
            await this.getVisibleElement(
                this.searchInput
            );


        await input.clear();


        await input.sendKeys(
            keyword
        );


        // 使用 Enter 提交搜索
        // 比依赖搜索按钮样式更稳定
        await input.sendKeys(
            Key.ENTER
        );


        // 等待进入搜索结果页
        await this.driver.wait(

            async () => {

                const currentUrl =
                    await this.driver
                        .getCurrentUrl();


                return currentUrl.includes(
                    "/search"
                );

            },

            10000,

            "搜索后没有进入搜索结果页"

        );

    }


    // ==================================================
    // 等待搜索结果完成
    // ==================================================

    async waitForResults() {

        await this.getVisibleElement(
            this.resultTitle,
            10000
        );

    }


    // ==================================================
    // 获取结果标题
    // ==================================================

    async getResultTitle() {

        const element =
            await this.getVisibleElement(
                this.resultTitle
            );


        return await element
            .getText();

    }


    // ==================================================
    // 获取搜索结果数量文本
    // ==================================================

    async getResultCountText() {

        const element =
            await this.getVisibleElement(
                this.resultCount
            );


        return await element
            .getText();

    }


    // ==================================================
    // 获取搜索框当前内容
    // ==================================================

    async getSearchInputValue() {

        const input =
            await this.getVisibleElement(
                this.searchInput
            );


        return await input
            .getAttribute(
                "value"
            );

    }


    // ==================================================
    // 指定资源是否显示
    // ==================================================

    async isResourceVisible(
        resourceName
    ) {

        try {

            const locator =
                By.xpath(
                    `//*[normalize-space(.)="${resourceName}"]`
                );


            const element =
                await this.getVisibleElement(
                    locator,
                    5000
                );


            return await element
                .isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==================================================
    // 获取当前 URL
    // ==================================================

    async getCurrentUrl() {

        return await this.driver
            .getCurrentUrl();

    }


    // ==================================================
    // 刷新搜索结果页
    // ==================================================

    async refresh() {

        await this.driver
            .navigate()
            .refresh();


        await this.waitForResults();

    }

}


module.exports = SearchPage;