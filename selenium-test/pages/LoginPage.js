const {
    By,
    until
} = require("selenium-webdriver");

const path = require("node:path");
const { pathToFileURL } = require("node:url");


class LoginPage {

    constructor(driver) {

        this.driver = driver;

        // 页面元素
        this.usernameInput =
            By.id("username");

        this.passwordInput =
            By.id("password");

        this.loginButton =
            By.id("loginBtn");

        this.resultText =
            By.id("result");
    }


    // ==============================
    // 打开登录页面
    // ==============================

    async open() {

        const filePath = path.resolve(
            __dirname,
            "../demo.html"
        );

        const fileUrl =
            pathToFileURL(filePath).href;

        await this.driver.get(
            fileUrl
        );

        // 等待用户名输入框出现
        await this.driver.wait(
            until.elementLocated(
                this.usernameInput
            ),
            5000
        );
    }


    // ==============================
    // 输入用户名
    // ==============================

    async enterUsername(username) {

        const element =
            await this.driver.findElement(
                this.usernameInput
            );

        await element.clear();

        if (username) {
            await element.sendKeys(
                username
            );
        }
    }


    // ==============================
    // 输入密码
    // ==============================

    async enterPassword(password) {

        const element =
            await this.driver.findElement(
                this.passwordInput
            );

        await element.clear();

        if (password) {
            await element.sendKeys(
                password
            );
        }
    }


    // ==============================
    // 点击登录按钮
    // ==============================

    async clickLogin() {

        await this.driver
            .findElement(
                this.loginButton
            )
            .click();
    }


    // ==============================
    // 完整登录操作
    // ==============================

    async login(
        username,
        password
    ) {

        await this.enterUsername(
            username
        );

        await this.enterPassword(
            password
        );

        await this.clickLogin();
    }


    // ==============================
    // 获取登录结果
    // ==============================

    async getResult() {

        const resultElement =
            await this.driver.wait(
                until.elementLocated(
                    this.resultText
                ),
                5000
            );

        return await resultElement
            .getText();
    }

}


module.exports = LoginPage;