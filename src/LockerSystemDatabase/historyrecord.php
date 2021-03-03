<?php
session_start();
if(isset($_SESSION["loggedin"]) != true) {
    header('Location: login.php');
    exit;
} else {
    $servername = "localhost";
    $username = $_SESSION["username"];
    $password = $_SESSION["password"];
    $dbname = "LOCKER_SYSTEM";
    $conn = mysqli_connect($servername, $username, $password, $dbname);
    $sql = "SELECT * FROM HISTORY_RECORD";
    $result = mysqli_query($conn, $sql);
}
?>
<html>
<header>
    <meta charseet="utf-8">
    <title>Gp3_8 Database</title>
    <link rel="stylesheet" href="bootstrap.min.css">
    <script src="bootstrap.min.js"></script>
</header>
<body>
    <nav class="navbar navbar-default">
        <div class="container-fluid">
            <div class="navbar-header">
                <a class="navbar-brand" href="welcome.php">Gp3_8 Locker System Database</a>
            </div>
            <ul class="nav navbar-nav">
                <li class="nav-item">
                    <a href="usersregistration.php" class="nav-link active">User registration</a>
                </li>
                <li class="nav-item">
                    <a href="historyrecord.php" class="nav-link active">History record</a>
                </li>
            </ul>
        </div>
    </nav>
    <div class="container">
        <h2>History record</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Student ID</th>
                    <th>Locker ID</th>
                    <th>Borrow Time</th>
                    <th>Return Time</th>
                </tr>
            </thead>
            <tbody>
                <?php
                if (mysqli_num_rows($result) > 0) {
                    while($row = mysqli_fetch_assoc($result)) {
                        echo '<tr>';
                        echo '<td>' . $row['ID'] . '</td>';
                        echo '<td>' . $row['STUDENT_ID'] . '</td>';
                        echo '<td>' . $row['LOCKER_ID'] . '</td>';
                        echo '<td>' . $row['BORROW_TIME'] . '</td>';
                        echo '<td>' . $row['RETURN_TIME'] . '</td>';
                        echo '</tr>';
                    }
                }
                ?>
            </tbody>
        </table>
    </div>
</body>
</html>