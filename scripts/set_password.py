from app.auth.security import hash_password
from app.db import close_pool, execute, open_pool


def set_password(username: str, password: str):
    password_hash = hash_password(password)

    execute(
        """
        UPDATE users
        SET password_hash = %s
        WHERE username = %s;
        """,
        (password_hash, username),
    )


def main():
    open_pool()

    set_password("admin_demo", "Admin123456")
    set_password("employee_demo", "Employee123456")
    set_password("operations_demo", "Operations123456")
    set_password("finance_demo", "Finance123456")
    set_password("admin", "Admin")
    set_password("user", "User")

    close_pool()

    print("密码设置完成")


if __name__ == "__main__":
    main()
